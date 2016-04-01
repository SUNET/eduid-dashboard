# NINS form

import deform
import urlparse
import requests
from datetime import datetime
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound, HTTPNotImplemented
from pyramid.i18n import get_localizer

from eduid_userdb.exceptions import UserOutOfSync
from eduid_userdb.nin import Nin
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN, normalize_nin
from eduiddashboard.views.mobiles import has_confirmed_mobile
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.utils import retrieve_modified_ts
from eduiddashboard.views import BaseFormView, BaseActionsView
from eduiddashboard import log
from eduiddashboard.validators import validate_nin_by_mobile
from eduiddashboard.verifications import set_nin_verified, new_verification_code, save_as_verified
from eduid_userdb.dashboard import DashboardUser
from eduiddashboard.idproofinglog import LetterProofing

import logging
logger = logging.getLogger(__name__)


def get_status(request, user):
    """
    Check if there is exist norEduPersonNIN active
    Else:
        Check is user has pending nin in verifications collection

    return msg and icon
    """

    completed_fields = 0
    pending_actions = None
    pending_action_type = ''
    verification_needed = -1

    all_nins = user.nins
    if all_nins.count:
        completed_fields = 1

    unverified_nins = get_not_verified_nins_list(request, user)

    if not all_nins.count and not unverified_nins:
        pending_actions = _('Add national identity number')
    if unverified_nins and request.registry.settings.get('enable_mm_verification'):
        pending_actions = _('Validation required for national identity number')
        pending_action_type = 'verify'
        verification_needed = len(unverified_nins) - 1

    status = {
        'completed': (completed_fields, 1)
    }
    if pending_actions:
        pending_actions = get_localizer(request).translate(pending_actions)
        status.update({
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'pending_action_type': pending_action_type,
            'verification_needed': verification_needed,
        })

    return status


def send_verification_code(request, user, nin, reference=None, code=None):
    """
    You need to replace the call to dummy_message with the govt
    message api
    """

    # Always normalize the nin before usage
    nin = normalize_nin(nin)

    if code is None or reference is None:
        reference, code = new_verification_code(request, 'norEduPersonNIN', nin, user, hasher=get_short_hash)

    language = request.context.get_preferred_language()

    request.msgrelay.nin_validator(reference, nin, code, language, nin, message_type='mm')
    request.stats.count('dashboard/nin_send_verification_code', 1)


def get_tab(request):
    label = _('Confirm Identity')
    return {
        'status': get_status,
        'label': get_localizer(request).translate(label),
        'id': 'nins',
    }


def get_not_verified_nins_list(request, user):
    """
    Return a list of all non-verified NINs.

    These come from the verifications mongodb collection, but we also double-check
    that anything in there that looks un-verified is not also found in user.get_nins().

    :param request:
    :param user:
    :return: List of NINs pending confirmation
    :rtype: [string]
    """
    users_nins = user.nins.to_list()
    res = []
    user_already_verified = []
    user_not_verified = []
    verifications = request.db.verifications.find({
        'model_name': 'norEduPersonNIN',
        'user_oid': user.user_id,
    }, sort=[('timestamp', 1)])
    if users_nins:
        for this in users_nins:
            if this.is_verified:
                user_already_verified.append(this.key)
            else:
                user_not_verified.append(this.key)
    for this in verifications:
        if this['verified'] and this['obj_id'] in user_not_verified:
            # Found to be verified after all, filter out from user_not_verified
            user_not_verified = [x for x in user_not_verified if not x == this['obj_id']]
        else:
            if this['obj_id'] not in user_already_verified:
                res.append(this['obj_id'])
    res += user_not_verified
    # As we no longer remove verification documents make the list items unique
    return list(set(res))


def get_active_nin(self):
    nins = self.user.nins.to_list()
    if self.user.nins.verified.count:
        return self.user.nins.primary.key
    elif nins:
        nin = nins[-1]
        if isinstance(nin, basestring):
            return nin
        return nin.key
    else:
        return None


def letter_status(request, user, nin):
    settings = request.registry.settings
    letter_url = settings.get('letter_service_url')
    state_url = urlparse.urljoin(letter_url, 'get-state')
    data = {'eppn': user.get_eppn()}
    response = requests.post(state_url, data=data)

    sent, result = False, 'error'
    msg = _('There was a problem with the letter service. '
            'Please try again later.')
    if response.status_code == 200:
        state = response.json()

        if 'letter_sent' in state:
            sent = True
            result = 'success'
            expires = datetime.utcfromtimestamp(int(state['letter_expires']))
            expires = expires.strftime('%Y-%m-%d')
            msg = _('A letter has already been sent to your official postal address. '
                    'The code enclosed will expire on ${expires}. '
                    'After that date you can restart the process if the letter was lost.',
                    mapping={'expires': expires})
        else:
            sent = False
            result = 'success'
            msg = _('When you click on the "Send" button a letter with a '
                    'verification code will be sent to your official postal address.')
            logger.info("Asking user {!r} if they want to send a letter.".format(user))
    else:
        logger.error('Error getting status from the letter service. Status code {!r}, msg "{}"'.format(
            response.status_code, response.text))
    return {
        'result': result,
        'message': get_localizer(request).translate(msg),
        'sent': sent
    }


def send_letter(request, user, nin):

    settings = request.registry.settings
    letter_url = settings.get('letter_service_url')
    send_letter_url = urlparse.urljoin(letter_url, 'send-letter')

    data = {'eppn': user.get_eppn(), 'nin': nin}
    response = requests.post(send_letter_url, data=data)
    result = 'error'
    msg = _('There was a problem with the letter service. '
            'Please try again later.')
    if response.status_code == 200:
        logger.info("Letter sent to user {!r}.".format(user))  # This log line moved here from letter_status function
        expires = response.json()['letter_expires']
        expires = datetime.utcfromtimestamp(int(expires))
        expires = expires.strftime('%Y-%m-%d')
        result = 'success'
        msg = _('A letter with a verification code has been sent to your '
                'official postal address. Please return to this page once you receive it.'
                ' The code will be valid until ${expires}.',
                mapping={'expires': expires})
    return {
        'result': result,
        'message': get_localizer(request).translate(msg),
    }


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    data_attribute = 'norEduPersonNIN'
    special_verify_messages = {
        'success': _('National identity number verified'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to your "Mina meddelanden" mailbox.'),
        'placeholder': _('Confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your "Mina meddelanden" mailbox'),
    }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify[self.data_attribute]

    def verify_action(self, data, post_data):
        """
        Only the active (the last one) NIN can be verified
        """
        nin, index = data.split()
        index = int(index)
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            new_nin = nins[index]
            if new_nin != nin:
                return self.sync_user()
        else:
            return self.sync_user()

#        if index != len(nins) - 1:
#            message = _("The provided nin can't be verified. You only "
#                        'can verify the last one')
#            return {
#                'result': 'bad',
#                'message': get_localizer(self.request).translate(message),
#            }

        return self._verify_action(new_nin, post_data)

    def verify_mb_action(self, data, post_data):
        """
        Only the active (the last one) NIN can be verified
        """
        nin, index = data.split()
        index = int(index)
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            new_nin = nins[index]
            if new_nin != nin:
                return self.sync_user()
        else:
            return self.sync_user()

#        if index != len(nins) - 1:
#            message = _("The provided nin can't be verified. You only "
#                        'can verify the last one')
#            return {
#                'result': 'bad',
#                'message': get_localizer(self.request).translate(message),
#            }

        validation = validate_nin_by_mobile(self.request, self.user, nin)
        result = validation['success'] and 'success' or 'error'
        if result == 'success':
            set_nin_verified(self.request, self.user, nin)
            model_name = 'norEduPersonNIN'
            try:
                self.context.save_dashboard_user(self.user)
                logger.info("Verified  by mobile, {!s} saved for user {!r}.".format(model_name, self.user))
                # Save the state in the verifications collection
                save_as_verified(self.request, 'norEduPersonNIN', self.user, nin)
            except UserOutOfSync:
                logger.info("Verified {!s} NOT saved for user {!r}. User out of sync.".format(model_name, self.user))
                raise
        settings = self.request.registry.settings
        msg = get_localizer(self.request).translate(validation['message'],
                mapping={
                'service_name': settings.get('mobile_service_name', 'Navet'),
                })
        return {
            'result': result,
            'message': msg,
            }

    def remove_action(self, data, post_data):
        """ Only not verified nins can be removed """
        raise HTTPNotImplemented  # Temporary remove the functionality

        nin, index = data.split()
        index = int(index)
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            remove_nin = nins[index]
            if remove_nin != nin:
                return self.sync_user()
        else:
            return self.sync_user()

        verifications = self.request.db.verifications
        verifications.remove({
            'model_name': self.data_attribute,
            'obj_id': remove_nin,
            'user_oid': self.user.user_id,
            'verified': False,
        })

        self.request.stats.count('dashboard/nin_remove', 1)
        message = _('National identity number has been removed')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def send_verification_code(self, data_id, reference, code):
        send_verification_code(self.request, self.user, data_id, reference, code)

    def resend_code_action(self, data, post_data):
        nin, index = data.split()
        index = int(index)
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            nin = nins[index]
        else:
            raise HTTPNotFound(_("No pending national identity numbers found."))

        send_verification_code(self.request, self.context.user, nin)

        self.request.stats.count('dashboard/nin_code_resend', 1)
        message = self.verify_messages['new_code_sent']
        return {
            'result': 'success',
            'message': message,
        }

    def verify_lp_action(self, data, post_data):
        '''
        verify by letter
        '''
        nin, index = data.split()
        index = int(index)
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            new_nin = nins[index]
            if new_nin != nin:
                return self.sync_user()
        else:
            return self.sync_user()

        return letter_status(self.request, self.user, nin)

    def send_letter_action(self, data, post_data):
        nin, index = data.split()
        return send_letter(self.request, self.user, nin)

    def finish_letter_action(self, data, post_data):
        nin, index = data.split()
        index = int(index)

        settings = self.request.registry.settings
        letter_url = settings.get('letter_service_url')
        verify_letter_url = urlparse.urljoin(letter_url, 'verify-code')

        code = post_data['verification_code']

        data = {'eppn': self.user.get_eppn(),
                'verification_code': code}
        logger.info("Posting letter verification code for user {!r}.".format(self.user))
        response = requests.post(verify_letter_url, data=data)
        logger.info("Received response from idproofing-letter after posting verification code "
                    "for user {!r}.".format(self.user))
        result = 'error'
        msg = _('There was a problem with the letter service. '
                'Please try again later.')
        if response.status_code != 200:
            # Do nothing, just return above error message and log microservice return code
            logger.info("Received status code {!s} from idproofing-letter after posting verification code "
                        "for user {!r}.".format(response.status_code, self.user))
        else:
            rdata = response.json().get('data', {})
            if rdata.get('verified', False) and nin == rdata.get('number', None):
                # Save data from successful verification call for later addition to user proofing collection
                rdata['created_ts'] = datetime.utcfromtimestamp(int(rdata['created_ts']))
                rdata['verified_ts'] = datetime.utcfromtimestamp(int(rdata['verified_ts']))
                letter_proofings = self.user.get_letter_proofing_data()
                letter_proofings.append(rdata)
                self.user.set_letter_proofing_data(letter_proofings)
                # Look up users official address at the time of verification per Kantara requirements
                logger.info("Looking up address via Navet for user {!r}.".format(self.user))
                user_postal_address = self.request.msgrelay.get_full_postal_address(rdata['number'])
                logger.info("Finished looking up address via Navet for user {!r}.".format(self.user))
                proofing_data = LetterProofing(self.user, rdata['number'], rdata['official_address'],
                                               rdata['transaction_id'], user_postal_address)
                # Log verification event and fail if that goes wrong
                logger.info("Logging proofing data for user {!r}.".format(self.user))
                if self.request.idproofinglog.log_verification(proofing_data):
                    logger.info("Finished logging proofing data for user {!r}.".format(self.user))
                    try:
                        # This is a hack to reuse the existing proofing functionality, the users code is
                        # verified by the micro service
                        set_nin_verified(self.request, self.user, nin)
                        try:
                            self.user.save(self.request)
                        except UserOutOfSync:
                            log.info("Verified norEduPersonNIN NOT saved for user {!r}. User out of sync.".format(
                                self.user))
                            raise
                        save_as_verified(self.request, 'norEduPersonNIN', self.user, nin)
                        logger.info("Verified NIN by physical letter saved "
                                    "for user {!r}.".format(self.user))
                    except UserOutOfSync:
                        log.error("Verified NIN by physical letter NOT saved "
                                  "for user {!r}. User out of sync.".format(self.user))
                        return self.sync_user()
                    else:
                        result = 'success'
                        msg = _('You have successfully verified your identity')
                else:
                    log.error('Logging of letter proofing data for user {!r} failed.'.format(self.user))
                    msg = _('Sorry, we are experiencing temporary technical '
                            'problems, please try again later.')
            else:
                log.info('User {!r} supplied wrong letter verification code or nin did not match.'.format(self.user))
                log.debug('NIN in dashboard: {!s}, NIN in idproofing-letter: {!s}'.format(nin,
                                                                                          rdata.get('number', None)))
                msg = _('Your verification code seems to be wrong, '
                        'please try again.')
        return {
            'result': result,
            'message': get_localizer(self.request).translate(msg),
        }


@view_config(route_name='nins', permission='edit',
             renderer='templates/nins-form.jinja2')
class NinsView(BaseFormView):
    """
    Provide the handler to emails
        * GET = Rendering template
        * POST = Creating or modifing nins,
                    return status and flash message
    """
    schema = NIN()

    route = 'nins'

    bootstrap_form_style = 'form-inline'

    get_active_nin = get_active_nin

    def __init__(self, *args, **kwargs):
        super(NinsView, self).__init__(*args, **kwargs)

        # All buttons for adding a nin, must have a name that starts with "add". This because the POST message, sent
        # from the button, must trigger the "add" validation part of a nin.
        self.buttons = ()
        if self.request.registry.settings.get('enable_mm_verification'):
            self.buttons += (deform.Button(name='add',
                             title=_('Mina Meddelanden')),)
        else:
            # Add a disabled button to for information purposes when Mina Meddelanden is disabled
            self.buttons += (deform.Button(name='NoMM',
                                           title=_('Mina Meddelanden'),
                                           css_class='btn btn-primary disabled'),)
        self.buttons += (deform.Button(name='add_by_mobile',
                                       title=_('Phone subscription'),
                                       css_class='btn btn-primary'),)
        self.buttons += (deform.Button(name='add_by_letter',
                                       title=_('Physical letter'),
                                       css_class='btn btn-primary'),)

    def appstruct(self):
        return {}

    def get_template_context(self):
        """
            Take active NIN (on am profile)
            Take NINs from verifications, sorted by older and compared with
            the present active NIN.
            If they are older, then don't take it.
            If there are not verified nins newer than the active NIN, then
            take them as not verified NINs
        """
        context = super(NinsView, self).get_template_context()

        settings = self.request.registry.settings
        enable_mm = settings.get('enable_mm_verification')

        context.update({
            'nins': self.user.nins,
            'not_verified_nins': get_not_verified_nins_list(self.request,
                                                            self.user),
            'active_nin': self.get_active_nin(),
            'has_mobile': has_confirmed_mobile(self.user),
            'enable_mm_verification': enable_mm,
        })
        if enable_mm:
            context.update({
                'nin_service_url': settings.get('nin_service_url'),
                'nin_service_name': settings.get('nin_service_name'),
            })

        return context

    def addition_with_code_validation(self, form):
        newnin = self.schema.serialize(form)
        newnin = newnin['norEduPersonNIN']
        newnin = normalize_nin(newnin)

        send_verification_code(self.request, self.user, newnin)
        return True

    def add_success_personal(self, ninform, msg):
        self.addition_with_code_validation(ninform)

        msg = get_localizer(self.request).translate(msg)
        self.request.session.flash(msg, queue='forms')

    def validate_post_data(self):
        self.schema = self.schema.bind(**self.get_bind_data())
        form = self.form_class(self.schema, buttons=self.buttons,
                               **dict(self.form_options))
        self.before(form)

        controls = self.request.POST.items()
        return form.validate(controls)

    def add_nin_external(self, data):
        try:
            validated = self.validate_post_data()
        except deform.exception.ValidationFailure as e:
            return {
                'status': 'failure',
                'data': e.error.asdict()
            }
        self.addition_with_code_validation(validated)
        self.request.stats.count('dashboard/nin_add_external', 1)
        return {
            'status': 'success'
        }

    def add_success_other(self, ninform):
        newnin = self.schema.serialize(ninform)
        newnin = newnin['norEduPersonNIN']

        newnin = normalize_nin(newnin)

        old_user = self.request.db.profiles.find_one({
            'norEduPersonNIN': newnin
            })

        if old_user:
            old_user = DashboardUser(data=old_user)
            retrieve_modified_ts(old_user, self.request.dashboard_userdb)
            old_user.nins.remove(newnin)
            self.context.save_dashboard_user(old_user)

        primary = False
        if self.user.nins.count == 0:
            primary = True
        newnin_obj = Nin(number=newnin, application='dashboard',
                verified=True, primary=primary)
        self.user.nins.add(newnin_obj)

        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            message = _('Your user profile is out of sync. Please '
                        'reload the page and try again.')
        else:
            message = _('Your national identity number has been confirmed')
        # Save the state in the verifications collection
        save_as_verified(self.request, 'norEduPersonNIN', self.user, newnin)
        self.request.session.flash(
                get_localizer(self.request).translate(message),
                queue='forms')
        self.request.stats.count('dashboard/nin_add_other', 1)

    def add_success(self, ninform):
        """ This method is bounded to the "add"-button by it's name """
        if self.context.workmode == 'personal':
            msg = _('A confirmation code has been sent to your government inbox. '
                    'Please click on "Pending confirmation" link below to enter '
                    'your confirmation code.')
            self.add_success_personal(ninform, msg)
        else:
            self.add_success_other(ninform)

    def add_by_mobile_success(self, ninform):
        """ This method is bounded to the "add_by_mobile"-button by it's name """
        self.add_success_other(ninform)

    def add_by_letter_success(self, ninform):
        """
        This method is bound to the "add_by_letter"-button by it's name
        """
        form = self.schema.serialize(ninform)
        nin = normalize_nin(form['norEduPersonNIN'])
        result = letter_status(self.request, self.user, nin)
        if result['result'] == 'success':
            result2 = send_letter(self.request, self.user, nin)
            if result2['result'] == 'success':
                new_verification_code(self.request, 'norEduPersonNIN',
                                      nin, self.user)
            msg = result2['message']
        else:
            msg = result['message']
        self.request.session.flash(msg, queue='forms')
