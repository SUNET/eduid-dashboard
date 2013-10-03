## Mobile phones forms

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Mobile
from eduiddashboard.sms import send_sms
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.verifications import get_verification_code, new_verification_code, verificate_code
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(user):
    """
    Check if all mobiles are verified already

    return msg and icon
    """

    mobiles = user.get('mobile', [])
    pending_actions = None

    if not mobiles:
        pending_actions = _('You have to add a mobile phone')
    else:
        for mobile in mobiles:
            if not mobile['verified']:
                pending_actions = _('You have to verificate some mobile phone')

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


def send_verification_code(request, user, mobile_number):
    code = new_verification_code(request.db, 'mobile', mobile_number, user, hasher=get_short_hash)
    msg = _('The confirmation code for mobile ${mobile_number} is ${code}', mapping={
        'mobile_number': mobile_number,
        'code': code,
    })
    msg = get_localizer(request).translate(msg)
    send_sms(request, mobile_number, msg)


def mark_as_verified_mobile(request, user, verified_mobile):
    mobiles = user['mobile']

    for mobile in mobiles:
        if mobile['mobile'] == verified_mobile:
            mobile['verified'] = True


@view_config(route_name='mobiles-actions', permission='edit')
class MobilesActionsView(BaseActionsView):

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
            'message': _('One mobile has been removed, please, wait'
                         ' before your changes are distributed '
                         'through all applications'),
        }

    def resend_code_action(self, index, post_data):
        mobiles = self.user.get('mobile', [])
        mobile_to_resend = mobiles[index]
        mobile_number = mobile_to_resend['mobile']

        send_verification_code(self.request, self.user, mobile_number)

        msg = _('A new verification code has been sent to your ${number} mobile number', mapping={
          'number': mobile_number,
        })
        msg = get_localizer(self.request).translate(msg)

        return {
            'result': 'ok',
            'message': msg,
        }

    def verify_action(self, index, post_data):
        mobile_to_verify = self.user.get('mobile', [])[index]
        mobile_number = mobile_to_verify['mobile']
        if 'code' in post_data:
            code_sent = post_data['code']
            verification_code = get_verification_code(self.request.db, 'mobile', mobile_number)
            if code_sent == verification_code['code']:
                verificate_code(self.request, 'mobile', code_sent)
                return {
                    'result': 'ok',
                    'message': _('The mobile phone has been verified'),
                }
            else:
                return {
                    'result': 'error',
                    'message': _('The confirmation code is not the one have been sent to your mobile phone')
                }
        else:
            return {
                'result': 'getcode',
                'message': _('Please revise your SMS inbox and fill below with the given code'),
                'placeholder': _('Mobile phone code'),
            }


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

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
