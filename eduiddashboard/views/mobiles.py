## Mobile phones forms

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Mobile
from eduiddashboard.sms import send_sms
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.verifications import get_verification_codes, new_verification_code, verificate_code
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


def mark_as_verified_mobile(request, context, verified_mobile):
    user = context.get_user()
    mobiles = user['mobile']

    for mobile in mobiles:
        if mobile['mobile'] == verified_mobile:
            mobile['verified'] = True

    # Do the save staff
    request.db.profiles.save(user, safe=True)
    request.context.propagate_user_changes(user)


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


    def verify_action(self, index, post_data):
        mobile_to_verify = self.user.get('mobile', [])[index]
        mobile_number = mobile_to_verify['mobile']
        if 'code' in post_data:
            code_sent = post_data['code']
            codes = get_verification_codes(self.request.db, 'mobiles', mobile_number)
            if code_sent in codes:
                verificate_code(self.request, 'mobiles', code_sent)

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
            code = new_verification_code(self.request.db, 'mobiles', mobile_number, hasher=get_short_hash)
            msg = _('The confirmation code for mobile ${mobile_number} is ${code}', mapping={
                'mobile_number': mobile_number,
                'code': code,
            })
            msg = get_localizer(self.request).translate(msg)
            send_sms(mobile_number, msg)

            return {
                'result': 'getcode',
                'message': _('A new verification message has been sent '
                             'to your mobile phone. Please revise your '
                             'SMS inbox and fill below with the given code'),
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

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
