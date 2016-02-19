## Mobile phones forms

import deform
from datetime import datetime

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduid_userdb.phone import PhoneNumber
from eduid_userdb.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Mobile
from eduiddashboard.utils import get_icon_string, get_short_hash, normalize_to_e_164
from eduiddashboard.verifications import new_verification_code
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(request, user):
    """
    Check if all mobiles are verified already

    return msg and icon
    """
    mobiles = user.phone_numbers
    pending_actions = None
    pending_action_type = ''
    verification_needed = -1
    completed = 0

    if not mobiles.count:
        pending_actions = _('Add mobile number')
        pending_actions = get_localizer(request).translate(pending_actions)
    else:
        for n, mobile in enumerate(mobiles.to_list()):
            if mobile.is_verified:
                completed = 1
            else:
                verification_needed = n
                pending_action_type = 'verify'
                pending_actions = _('A mobile phone number is pending '
                                    'confirmation')
                pending_actions = get_localizer(request).translate(
                                                        pending_actions)

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'pending_action_type': pending_action_type,
            'completed': (completed, 1),
            'verification_needed': verification_needed,
        }
    return {
        'completed': (completed, 1),
    }


def has_confirmed_mobile(user):
    mobiles = user.phone_numbers.to_list()
    for m in mobiles:
        if m.is_verified:
            return True
    return False


def get_tab(request):
    label = _('Mobile phone numbers')
    return {
        'status': get_status,
        'label': get_localizer(request).translate(label),
        'id': 'mobiles',
    }


def send_verification_code(request, user, mobile_number, reference=None, code=None):
    if code is None or reference is None:
        reference, code = new_verification_code(request, 'mobile', mobile_number, user, hasher=get_short_hash)

    user_language = request.context.get_preferred_language()
    request.msgrelay.mobile_validator(reference, mobile_number, code, user_language)
    request.stats.count('dashboard/mobile_number_send_verification_code', 1)


@view_config(route_name='mobiles-actions', permission='edit')
class MobilesActionsView(BaseActionsView):
    data_attribute = 'mobile'
    special_verify_messages = {
        'success': _('The mobile phone number has been verified'),
        'error': _('The confirmation code used is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to the mobile phone number {data}'),
        'placeholder': _('Mobile phone code'),
        'new_code_sent': _('A new confirmation code has been sent to your mobile number'),
    }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify['number']

    def remove_action(self, index, post_data):
        mobiles = self.user.phone_numbers.to_list()
        mobile_to_remove = mobiles[index]
        self.user.phone_numbers.remove(mobile_to_remove.number)

        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            return self.sync_user()

        self.request.stats.count('dashboard/mobile_number_removed', 1)
        message = _('Mobile phone number was successfully removed')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def setprimary_action(self, index, post_data):
        mobiles = self.user.phone_numbers.to_list()

        try:
            mobile = mobiles[index]
        except IndexError:
            return self.sync_user()

        if not mobile.is_verified:
            message = _('You need to confirm your mobile number '
                        'before it can become primary')
            return {
                'result': 'bad',
                'message': get_localizer(self.request).translate(message),
            }

        self.user.phone_numbers.primary = mobile.number
        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            return self.sync_user()

        self.request.stats.count('dashboard/mobile_number_set_primary', 1)
        message = _('Mobile phone number was successfully made primary')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def send_verification_code(self, data_id, reference, code):
        send_verification_code(self.request, self.user, data_id, reference, code)


@view_config(route_name='mobiles', permission='edit',
             renderer='templates/mobiles-form.jinja2')
class MobilesView(BaseFormView):
    """
    Change user mobiles
        * GET = Rendering template
        * POST = Creating or modifing mobiles data,
                    return status and flash message
    """

    schema = Mobile()
    route = 'mobiles'

    buttons = (deform.Button(name='add', title=_('Add')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(MobilesView, self).get_template_context()
        context.update({
            'mobiles': self.user.phone_numbers.to_list(),
        })
        return context

    def add_success(self, mobileform):
        mobile_number = self.schema.serialize(mobileform)['mobile']
        mobile_number = normalize_to_e_164(self.request, mobile_number)
        mobile = PhoneNumber(data={'number':  mobile_number,
                                   'verified': False,
                                   'primary': False,
                                   'created_ts': datetime.utcnow()
                                   })
        self.user.phone_numbers.add(mobile)
        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            self.sync_user()

        else:
            send_verification_code(self.request, self.user, mobile_number)

            self.request.session.flash(_('Changes saved'),
                                   queue='forms')
            msg = _('A confirmation code has been sent to your mobile phone. '
                'Please click on the "Pending confirmation" link below and enter your confirmation code.')
            msg = get_localizer(self.request).translate(msg)
            self.request.session.flash(msg,
                                   queue='forms')
