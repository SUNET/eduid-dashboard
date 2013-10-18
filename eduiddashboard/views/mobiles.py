## Mobile phones forms

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Mobile
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.verifications import new_verification_code
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(user):
    """
    Check if all mobiles are verified already

    return msg and icon
    """
    mobiles = user.get('mobile', [])
    pending_actions = None

    if not mobiles:
        pending_actions = _('Add mobile phone number')
    else:
        for mobile in mobiles:
            if not mobile['verified']:
                pending_actions = _('A mobile phone number is pending confirmation')

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'completed': (0, 1),
        }
    return {
        'completed': (1, 1),
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Mobiles'),
        'id': 'mobiles',
    }


def send_verification_code(request, user, mobile_number, code=None):
    if code is None:
        code = new_verification_code(request, 'mobile', mobile_number, user,
                                     hasher=get_short_hash)

    user_language = request.context.get_preferred_language()

    request.msgrelay.mobile_validator(mobile_number, code, user_language)


def mark_as_verified_mobile(request, user, verified_mobile):
    mobiles = user['mobile']

    for mobile in mobiles:
        if mobile['mobile'] == verified_mobile:
            mobile['verified'] = True


@view_config(route_name='mobiles-actions', permission='edit')
class MobilesActionsView(BaseActionsView):
    data_attribute = 'mobile'
    verify_messages = {
        'ok': _('The mobile phone number has been verified'),
        'error': _('The confirmation code used is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent your mobile phone number'),
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
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'mobile': mobiles,
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('Mobile phone number was successfully removed'),
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

    buttons = ('add', )

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
        mobile_number = mobile['mobile']
        mobile['verified'] = False

        mobiles = self.user.get('mobile', [])
        mobiles.append(mobile)

        # update the session data
        self.user['mobile'] = mobiles
        mobile_identifier = len(mobiles) - 1

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'mobile': mobiles,
            }
        }, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        send_verification_code(self.request, self.user, mobile_number)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')
        msg = _('A confirmation code has been sent to your mobile phone. '
                'Please enter your confirmation code <a href="#" class="verifycode" data-identifier="${identifier}">here</a>',
                mapping={'identifier': mobile_identifier})
        msg = get_localizer(self.request).translate(msg)
        self.request.session.flash(msg,
                                   queue='forms')
