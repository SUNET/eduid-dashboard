# NINS form

import deform
from datetime import datetime
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound, HTTPNotImplemented
from pyramid.i18n import get_localizer

from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN, normalize_nin
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.views import BaseFormView, BaseActionsView, BaseWizard
from eduiddashboard.validators import NINRegisteredMobileValidator
from eduiddashboard import log
from eduid_am.user import User

from eduiddashboard.verifications import (new_verification_code,
                                          save_as_verified)

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

    all_nins = user.get_nins()
    if all_nins:
        completed_fields = 1

    unverified_nins = get_not_verified_nins_list(request, user)

    if not all_nins and not unverified_nins:
        pending_actions = _('Add national identity number')
    if unverified_nins:
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
    if code is None or reference is None:
        reference, code = new_verification_code(request, 'norEduPersonNIN', nin, user, hasher=get_short_hash)

    language = request.context.get_preferred_language()

    request.msgrelay.nin_validator(reference, nin, code, language, nin, message_type='mm')


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
    active_nins = user.get_nins()
    nins = []
    verifications = request.db.verifications
    not_verified_nins = verifications.find({
        'model_name': 'norEduPersonNIN',
        'user_oid': user.get_id(),
    }, sort=[('timestamp', 1)])
    if active_nins:
        active_nin = active_nins[-1]
        nin_found = False
        for nin in not_verified_nins:
            if active_nin == nin['obj_id']:
                nin_found = True
            elif nin_found and not nin['verified']:
                nins.append(nin['obj_id'])
    else:
        for nin in not_verified_nins:
            if not nin['verified']:
                nins.append(nin['obj_id'])
    # As we no longer remove verification documents make the list items unique
    return list(set(nins))


def get_active_nin(self):
    active_nins = self.user.get_nins()
    if active_nins:
        return active_nins[-1]
    else:
        return None


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    data_attribute = 'norEduPersonNIN'
    special_verify_messages = {
        'ok': _('National identity number verified'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to your "Min myndighetspost" mailbox.'),
        'placeholder': _('National identity number confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your "Min myndighetspost" mailbox'),
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
            verify_nin = nins[index]
            if verify_nin != nin:
                return self.sync_user()
        else:
            return self.sync_user()

        if index != len(nins) - 1:
            message = _("The provided nin can't be verified. You only "
                        'can verify the last one')
            return {
                'result': 'bad',
                'message': get_localizer(self.request).translate(message),
            }

        return self._verify_action(verify_nin, post_data)

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
            'user_oid': self.user.get_id(),
            'verified': False,
        })

        message = _('National identity number has been removed')
        return {
            'result': 'ok',
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

        message = self.verify_messages['new_code_sent']
        return {
            'result': 'ok',
            'message': message,
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

    # All buttons for adding a nin, must have a name that starts with "add". This because the POST message, sent
    # from the button, must trigger the "add" validation part of a nin.
    buttons = (deform.Button(name='add',
                             title=_('Add national identity number')),
               deform.Button(name='add_by_mobile',
                             title=_('Verify by registered phone'),
                             css_class='btn btn-primary'),
               )

    bootstrap_form_style = 'form-inline'

    get_active_nin = get_active_nin

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

        context.update({
            'nins': self.user.get_nins(),
            'not_verified_nins': get_not_verified_nins_list(self.request,
                                                            self.user),
            'active_nin': self.get_active_nin(),
            'nin_service_url': settings.get('nin_service_url'),
            'nin_service_name': settings.get('nin_service_name'),
            'open_wizard': nins_open_wizard(self.context, self.request),
        })

        return context

    def addition_with_code_validation(self, form):
        newnin = self.schema.serialize(form)
        newnin = newnin['norEduPersonNIN']
        newnin = normalize_nin(newnin)

        send_verification_code(self.request, self.user, newnin)

    def add_success_personal(self, ninform, msg):
        self.addition_with_code_validation(ninform)

        msg = get_localizer(self.request).translate(msg)
        self.request.session.flash(msg, queue='forms')

    def add_nin_external(self, data):
        self.schema = self.schema.bind(**self.get_bind_data())
        form = self.form_class(self.schema, buttons=self.buttons,
                               **dict(self.form_options))
        self.before(form)

        controls = self.request.POST.items()
        try:
            validated = form.validate(controls)
        except deform.exception.ValidationFailure as e:
            return {
                'status': 'failure',
                'data': e.error.asdict()
            }
        self.addition_with_code_validation(validated)
        return {
            'status': 'ok'
        }

    def add_success_other(self, ninform):
        newnin = self.schema.serialize(ninform)
        newnin = newnin['norEduPersonNIN']

        newnin = normalize_nin(newnin)

        old_user = self.request.db.profiles.find_one({
            'norEduPersonNIN': newnin
            })

        if old_user:
            old_user = User(old_user)
            old_user.retrieve_modified_ts(self.request.db.profiles)
            nins = [nin for nin in old_user.get_nins() if nin != newnin]
            old_user.set_nins(nins)
            addresses = [a for a in old_user.get_addresses() if not a['verified']]
            old_user.set_addresses(addresses)
            old_user.save(self.request)

        nins = self.user.get_nins()
        nins.append(newnin)
        self.user.set_nins(nins)
        self.user.retrieve_address(self.request, newnin)

        try:
            self.user.save(self.request)
        except UserOutOfSync:
            message = _('User data out of sync. Please try again.')
        else:
            message = _('Your national identity number has been confirmed')
        # Save the state in the verifications collection
        save_as_verified(self.request, 'norEduPersonNIN',
                            self.user.get_id(), newnin)
        self.request.session.flash(
                get_localizer(self.request).translate(message),
                queue='forms')

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

@view_config(route_name='wizard-nins', permission='edit', renderer='json')
class NinsWizard(BaseWizard):
    model = 'norEduPersonNIN'
    route = 'wizard-nins'
    last_step = 1

    def step_0(self, data):
        """ The NIN form """

        nins_view = NinsView(self.context, self.request)

        return nins_view.add_nin_external(data)

    def step_1(self, data):
        """ The verification code form """
        nins_action_view = NINsActionsView(self.context, self.request)

        result = nins_action_view._verify_action(normalize_nin(self.datakey), data)

        if result['result'] == 'ok':
            return {
                'status': 'ok',
            }
        else:
            return {
                'status': 'failure',
                'data': {
                    'code': result['message']
                }
            }

    def get_template_context(self):
        context = super(NinsWizard,self).get_template_context()
        context['title'] = _('Add NIN with MM confirmation')
        return context

    def resendcode(self):
        if self.datakey is None:
            message = _("Your national identity number confirmation request "
                        "can not be found")
            message = get_localizer(self.request).translate(message)
            return {
                'status': 'failure',
                'text': message
            }
        send_verification_code(self.request,
                               self.context.user,
                               self.datakey)
        text = NINsActionsView.special_verify_messages.get('new_code_sent',
            NINsActionsView.default_verify_messages.get('new_code_sent', ''))
        return {
            'status': 'ok',
            'text': text,
        }


def nins_open_wizard(context, request):
    if context.workmode != 'personal':
        return (False, None)
    ninswizard = NinsWizard(context, request)

    datakey = ninswizard.obj.get('datakey', None)
    open_wizard = ninswizard.is_open_wizard()

    logger.debug('Wizard params: open: {}, datakey: {}'.format(
                   str(open_wizard),
                   datakey))

    return (open_wizard, datakey)
