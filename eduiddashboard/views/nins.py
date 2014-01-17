# NINS form

import deform

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.i18n import get_localizer

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN, normalize_nin
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.views import BaseFormView, BaseActionsView, BaseWizard
from eduiddashboard import log

from eduiddashboard.verifications import (new_verification_code,
                                          save_as_verificated)


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

    if user.get('norEduPersonNIN', []):
        completed_fields = 1

    all_nins = user.get('norEduPersonNIN', [])
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
        status.update({
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'pending_action_type': pending_action_type,
            'verification_needed': verification_needed,
        })

    return status


def send_verification_code(request, user, nin, code=None):
    """
    You need to replace the call to dummy_message with the govt
    message api
    """

    if code is None:
        code = new_verification_code(request, 'norEduPersonNIN', nin, user,
                                     hasher=get_short_hash)

    language = request.context.get_preferred_language()

    request.msgrelay.nin_validator(nin, code, language)


def mark_as_verified_nin(request, user, verified_nin):
    """
        Replace old nin with the new verified nin.
    """
    if user.get('norEduPersonNIN', None) is None:
        user['norEduPersonNIN'] = [verified_nin]
    else:
        user['norEduPersonNIN'].append(verified_nin)


def retrieve_postal_address(request, user, verified_nin):
    """
        Function to get the official postal address from
        the government service
    """
    address = request.msgrelay.get_postal_address(verified_nin)

    address['type'] = 'official'
    address['verified'] = True

    user_addresses = user.get('postalAddress', [])

    changed = False
    for user_address in user_addresses:
        if user_address.get('type') == 'official':
            user_addresses.remove(user_address)
            user_addresses.append(address)
            changed = True

    if not changed:
        user_addresses.append(address)

    user['postalAddress'] = user_addresses
    request.db.profiles.save(user, safe=True)
    request.context.propagate_user_changes(user)


def post_verified_nin(request, user, verified_nin):
    """
        Function to do things after the nin is fully verified
    """
    log.debug('Retrieving postal address from NIN service')
    retrieve_postal_address(request, user, verified_nin)


def get_tab():
    return {
        'status': get_status,
        'label': _('Confirm Identity'),
        'id': 'nins',
    }


def get_not_verified_nins_list(request, user):
    active_nins = user.get('norEduPersonNIN', [])
    nins = []
    verifications = request.db.verifications
    not_verified_nins = verifications.find({
        'model_name': 'norEduPersonNIN',
        'user_oid': user['_id'],
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

    return nins


def get_active_nin(self):
    active_nins = self.user.get('norEduPersonNIN', [])
    if active_nins:
        return active_nins[-1]
    else:
        return None


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    data_attribute = 'norEduPersonNIN'
    verify_messages = {
        'ok': _('National identity number verified'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('A confirmation code for NIN {data} has been sent to your govt mailbox'),
        'placeholder': _('National identity number confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your govt mailbox'),
    }

    get_active_nin = get_active_nin

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify[self.data_attribute]

    def verify_action(self, index, post_data):
        """ Only the active (the last one) NIN can be verified """
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            verify_nin = nins[index]
        else:
            raise HTTPNotFound("The index provides can't be found")

        if index != len(nins) - 1:
            return {
                'result': 'bad',
                'message': _("The provided nin can't be verified. You only "
                             'can verify the last one'),
            }

        return super(NINsActionsView, self)._verify_action(verify_nin,
                                                           post_data)

    def remove_action(self, index, post_data):
        """ Only not verified nins can be removed """
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            remove_nin = nins[index]
        else:
            raise HTTPNotFound("The index provides can't be found")

        verifications = self.request.db.verifications
        verifications.remove({
            'model_name': self.data_attribute,
            'obj_id': remove_nin,
            'user_oid': self.user['_id'],
            'verified': False,
        })

        return {
            'result': 'ok',
            'message': _('National identity number has been removed'),
        }

    def send_verification_code(self, data_id, code):
        send_verification_code(self.request, self.user, data_id, code)


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

    buttons = (deform.Button(name='add',
                             title=_('Add national identity number')), )

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
            'nins': self.user.get('norEduPersonNIN', []),
            'not_verified_nins': get_not_verified_nins_list(self.request,
                                                            self.user),
            'active_nin': self.get_active_nin(),
            'nin_service_url': settings.get('nin_service_url'),
            'nin_service_name': settings.get('nin_service_name'),
        })

        return context

    def addition_with_code_validation(self, form):
        newnin = self.schema.serialize(form)
        newnin = newnin['norEduPersonNIN']

        newnin = normalize_nin(newnin)

        send_verification_code(self.request, self.user, newnin)

    def add_success_personal(self, ninform):

        self.addition_with_code_validation(ninform)

        msg = _('A confirmation code has been sent to your govt inbox. '
                'Please click on "Pending confirmation" link below to enter.'
                'your confirmation code')

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

        nins = self.user.get('norEduPersonNIN', [])

        nins.append(newnin)

        self.user['norEduPersonNIN'] = nins

        # Save the state in the verifications collection
        save_as_verificated(self.request, 'norEduPersonNIN',
                            self.user['_id'], newnin)

        # Do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')

    def add_success(self, ninform):
        if self.context.workmode == 'personal':
            self.add_success_personal(ninform)
        else:
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

        result = nins_action_view._verify_action(self.datakey, data)

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

    def resendcode(self):

        if self.datakey is None:
            message = _("Your National identity number validation request "
                        "can't be found")
            message = get_localizer(self.request).translate(message)
            return {
                'status': 'failure',
                'text': message
            }
        message = NINsActionsView.verify_messages['new_code_sent']
        message = get_localizer(self.request).translate(message)
        send_verification_code(self.request, self.context.user, self.datakey)

        return {
            'status': 'ok',
            'text': message,
        }


def nins_open_wizard(context, request):
    if context.workmode != 'personal':
        return (False, None)
    ninswizard = NinsWizard(context, request)

    datakey = ninswizard.obj.get('datakey', None)
    open_wizard = ninswizard.is_open_wizard()

    return (open_wizard, datakey)
