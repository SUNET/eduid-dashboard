## Mobile phones forms

import deform
from datetime import datetime

from pyramid.i18n import get_localizer
from pyramid.view import view_config

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
    mobiles = user.get_mobiles()
    pending_actions = None
    pending_action_type = ''
    verification_needed = -1
    completed = 0

    if not mobiles:
        pending_actions = _('Add mobile phone number')
        pending_actions = get_localizer(request).translate(pending_actions)
    else:
        for n, mobile in enumerate(mobiles):
            if mobile['verified']:
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
        return data_to_verify['mobile']

    def remove_action(self, index, post_data):
        mobiles = self.user.get_mobiles()
        mobile_to_remove = mobiles[index]
        mobiles.remove(mobile_to_remove)

        self.user.set_mobiles(mobiles)

        try:
            self.user.save(self.request)
        except UserOutOfSync:
            return self.sync_user()

        message = _('Mobile phone number was successfully removed')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def setprimary_action(self, index, post_data):
        mobiles = self.user.get_mobiles()

        if index > len(mobiles):
            message = _("That mobile phone number doesn't exists")
            return {
                'result': 'bad',
                'message': get_localizer(self.request).translate(message),
            }

        if index > len(mobiles):
            message = _("You need to verify that mobile phone number "
                        "before be able to set as primary")
            return {
                'result': 'bad',
                'message': get_localizer(self.request).translate(message),
            }

        # set all to False, and then set the new primary to True using the index
        for mobile in mobiles:
            mobile['primary'] = False

        assert(mobiles[index]['verified'])  # double check
        mobiles[index]['primary'] = True

        self.user.set_mobiles(mobiles)
        try:
            self.user.save(self.request)
        except UserOutOfSync:
            return self.sync_user()


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

    buttons = (deform.Button(name='add', title=_('Add mobile phone number')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(MobilesView, self).get_template_context()
        context.update({
            'mobiles': self.user.get_mobiles(),
        })
        return context

    def add_success(self, mobileform):
        mobile_number = self.schema.serialize(mobileform)['mobile']
        mobile_number = normalize_to_e_164(self.request, mobile_number)
        mobile = {'mobile':  mobile_number,
                  'verified': False,
                  'primary': False,
                  'added_timestamp': datetime.utcnow()
                  }
        self.user.add_mobile(mobile)
        try:
            self.user.save(self.request)
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
