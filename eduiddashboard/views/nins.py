# NINS form

import deform
from datetime import datetime
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.i18n import get_localizer

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN, normalize_nin
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.views import BaseFormView, BaseActionsView, BaseWizard
from eduiddashboard import log
from eduid_am.user import User

from eduiddashboard.verifications import (new_verification_code,
                                          save_as_verified, remove_nin_from_others)


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

    verified_nins = get_verified_nins_list(user)
    if verified_nins:
        completed_fields = 1

    unverified_nins = get_not_verified_nins_list(request, user)

    if not verified_nins and not unverified_nins:
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


def send_nin_verification_code(request, user, nin, reference=None, code=None):
    """
    You need to replace the call to dummy_message with the govt
    message api
    """

    if code is None or reference is None:
        reference, code = new_verification_code(request, 'norEduPersonNIN', nin, user, hasher=get_short_hash)

    language = request.context.get_preferred_language()

    request.msgrelay.nin_validator(reference, nin, code, language)


def get_tab(request):
    label = _('Confirm Identity')
    return {
        'status': get_status,
        'label': get_localizer(request).translate(label),
        'id': 'nins',
    }


def get_verified_nins_list(user):
    """
    Return a list of all verified NINs.

    :param user:
    :return: List of NINs pending confirmation
    :rtype: [string]
    """
    verified_nins = []
    for item in user.get_nins():
        if isinstance(item, dict) and item['verified']:
            verified_nins.append(item['nin'])
        if isinstance(item, str):  # Backwards compatability
            verified_nins.append(item)
    return verified_nins


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

    not_verified_nins = []
    for item in user.get_nins():
        if isinstance(item, dict) and not item['verified']:
            not_verified_nins.append(item['nin'])

    # Backwards compatability
    doc = {'model_name': 'norEduPersonNIN', 'user_oid': user.get_id()}
    verification_collection_nins = request.db.verifications.find(doc, sort=[('timestamp', 1)])
    for nin in verification_collection_nins:
        if not nin['verified'] and not nin['obj_id'] in not_verified_nins:
            not_verified_nins.append(nin['obj_id'])

    return not_verified_nins


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    data_attribute = 'norEduPersonNIN'
    special_verify_messages = {
        'success': _('National identity number verified'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to your "Min myndighetspost" mailbox.'),
        'placeholder': _('National identity number confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your "Min myndighetspost" mailbox'),
    }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify[self.data_attribute]

    def verify_action(self, index, post_data):
        nins = get_not_verified_nins_list(self.request, self.user)

        try:
            verify_nin = nins[index]
        except IndexError:
            # XXX Could happen with more than one dashboard, should ideally not use index?
            raise HTTPNotFound("Something went wrong. Please reload the page.")

        return super(NINsActionsView, self)._verify_action(verify_nin, post_data)

    def remove_action(self, index, post_data):
        """ Only not verified nins can be removed """
        not_verified_nins = get_not_verified_nins_list(self.request, self.user)
        try:
            remove_nin = not_verified_nins[index]
            for item in self.user.get_nins():
                nin = None
                if isinstance(item, dict):
                    nin = item['nin']
                elif isinstance(item, str):  # Backwards compatibility
                    nin = item
                if nin == remove_nin:
                    nins = self.user.get_nins()
                    nins.remove(item)
                    self.user.set_nins(nins)
                    self.user.save(self.request)
            # Backwards compatibility
            self.request.db.verifications.remove({
                'model_name': self.data_attribute,
                'obj_id': remove_nin,
                'user_oid': self.user.get_id(),
                'verified': False,
            })
        except IndexError:
            # XXX Could happen with more than one dashboard, should ideally not use index?
            raise HTTPNotFound("Something went wrong. Please reload the page.")

        message = _('National identity number has been removed')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def send_verification_code(self, data_id, reference, code):
        send_nin_verification_code(self.request, self.user, data_id, reference, code)

    def resend_code_action(self, index, post_data):
        nins = get_not_verified_nins_list(self.request, self.user)

        if len(nins) > index:
            nin = nins[index]
        else:
            raise HTTPNotFound(_("No pending national identity numbers found."))

        send_nin_verification_code(self.request, self.context.user, nin)

        message = self.verify_messages['new_code_sent']
        return {
            'result': 'success',
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

    buttons = (deform.Button(name='add',
                             title=_('Add national identity number')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(NinsView, self).get_template_context()

        settings = self.request.registry.settings

        context.update({
            'not_verified_nins': get_not_verified_nins_list(self.request, self.user),
            'verified_nins': get_verified_nins_list(self.user),
            'nin_service_url': settings.get('nin_service_url'),
            'nin_service_name': settings.get('nin_service_name'),
        })

        return context

    def addition_with_code_validation(self, nin):
        nin_dict = {
            'nin': nin,
            'verified': False,
            'added_timestamp': datetime.utcnow()
        }
        nins = self.user.get_nins()
        nins.append(nin_dict)
        self.user.set_nins(nins)
        self.user.save(self.request)
        send_nin_verification_code(self.request, self.user, nin)

    def add_success_personal(self, ninform):
        nin = normalize_nin(self.schema.serialize(ninform)['norEduPersonNIN'])
        self.addition_with_code_validation(nin)

        msg = _('A confirmation code has been sent to your government inbox. '
                'Please click on "Pending confirmation" link below to enter '
                'your confirmation code.')

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
            'status': 'success'
        }

    def add_success_other(self, ninform):
        nin = normalize_nin(self.schema.serialize(ninform)['norEduPersonNIN'])
        remove_nin_from_others(nin, self.request)

        self.user.add_verified_nin('Set by admin user', nin)  # TODO: Need reference to admin user

        self.user.save(self.request)
        message = _('Changes saved')
        self.request.session.flash(get_localizer(self.request).translate(message), queue='forms')

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

        result = nins_action_view._verify_action(normalize_nin(self.datakey), data)

        if result['result'] == 'success':
            return {
                'status': 'success',
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
            message = _("Your national identity number confirmation request "
                        "can not be found")
            message = get_localizer(self.request).translate(message)
            return {
                'status': 'failure',
                'text': message
            }
        send_verification_code(self.request, self.context.user, self.datakey)

        message = NINsActionsView.verify_messages['new_code_sent']
        return {
            'status': 'success',
            'text': message,
        }


def nins_open_wizard(context, request):
    if context.workmode != 'personal':
        return (False, None)
    ninswizard = NinsWizard(context, request)

    datakey = ninswizard.obj.get('datakey', None)
    open_wizard = ninswizard.is_open_wizard()

    return (open_wizard, datakey)
