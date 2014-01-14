## Mobile phones forms

import deform

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Mobile
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.verifications import new_verification_code
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(request, user):
    """
    Check if all mobiles are verified already

    return msg and icon
    """
    mobiles = user.get('mobile', [])
    pending_actions, verification_needed = None, -1

    if not mobiles:
        pending_actions = _('Add mobile phone number')
    else:
        for n, mobile in enumerate(mobiles):
            if not mobile['verified']:
                verification_needed = n
                pending_actions = _('A mobile phone number is pending confirmation')

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'completed': (0, 1),
            'verification_needed': verification_needed,
        }
    return {
        'completed': (1, 1),
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Mobile phone numbers'),
        'id': 'mobiles',
    }


def send_verification_code(request, user, mobile_number, code=None):
    if code is None:
        code = new_verification_code(request, 'mobile', mobile_number, user,
                                     hasher=get_short_hash)

    user_language = request.context.get_preferred_language()

    request.msgrelay.mobile_validator(mobile_number, code, user_language)


def convert_to_e_164(request, mobile):
    """ convert a mobile to international notation +XX XXXXXXXX """
    if mobile['mobile'].startswith(u'0'):
        country_code = request.registry.settings.get('default_country_code')
        mobile['mobile'] = country_code + mobile['mobile'].lstrip(u'0')


def mark_as_verified_mobile(request, user, verified_mobile):
    mobiles = user['mobile']

    for mobile in mobiles:
        if mobile['mobile'] == verified_mobile:
            mobile['verified'] = True
            if len(mobiles) == 1:
                mobile['primary'] = True


@view_config(route_name='mobiles-actions', permission='edit')
class MobilesActionsView(BaseActionsView):
    data_attribute = 'mobile'
    verify_messages = {
        'ok': _('The mobile phone number has been verified'),
        'error': _('The confirmation code used is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to your mobile phone number'),
        'placeholder': _('Mobile phone code'),
        'new_code_sent': _('A new confirmation code has been sent to your mobile number'),
    }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify['mobile']

    def remove_action(self, index, post_data):
        mobiles = self.user.get('mobile', [])
        mobile_to_remove = mobiles[index]
        mobiles.remove(mobile_to_remove)

        self.user['mobile'] = mobiles

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('Mobile phone number was successfully removed'),
        }

    def setprimary_action(self, index, post_data):
        mobiles = self.user.get('mobile', [])

        if index > len(mobiles):
            return {
                'result': 'bad',
                'message': _("That mobile phone number doesn't exists"),
            }

        if index > len(mobiles):
            return {
                'result': 'bad',
                'message': _("You need to verify that mobile phone number "
                             "before be able to set as primary"),
            }

        # set all to False, and then set the new primary to True using the index
        for mobile in mobiles:
            mobile['primary'] = False

        assert(mobiles[index]['verified'])  # double check
        mobiles[index]['primary'] = True

        self.user['mobile'] = mobiles

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('Mobile phone number was successfully made primary'),
        }

    def send_verification_code(self, data_id, code):
        send_verification_code(self.request, self.user, data_id, code)


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
            'mobiles': self.user.get('mobile', []),
        })
        return context

    def add_success(self, mobileform):
        mobile = self.schema.serialize(mobileform)
        convert_to_e_164(self.request, mobile)
        mobile_number = mobile['mobile']
        mobile['verified'] = False
        mobile['primary'] = False

        mobiles = self.user.get('mobile', [])
        mobiles.append(mobile)

        # update the session data
        self.user['mobile'] = mobiles

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        send_verification_code(self.request, self.user, mobile_number)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')
        msg = _('A confirmation code has been sent to your mobile phone. '
                'Please click on the "Pending confirmation" link below and enter your confirmation code.')
        msg = get_localizer(self.request).translate(msg)
        self.request.session.flash(msg,
                                   queue='forms')
