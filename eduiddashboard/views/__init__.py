import json

from pyramid.httpexceptions import HTTPOk
from pyramid.i18n import get_localizer
from pyramid.response import Response

from pyramid_deform import FormView

from eduiddashboard.forms import BaseForm
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import get_short_hash
from eduiddashboard.verifications import get_verification_code, verificate_code, new_verification_code


def get_dummy_status(user):
    return None


class BaseFormView(FormView):
    form_class = BaseForm
    route = ''
    base_route = 'profile-editor'

    buttons = ('save', )
    use_ajax = True

    def __init__(self, context, request):
        super(BaseFormView, self).__init__(request)
        self.user = context.user
        self.context = context

        self.classname = self.__class__.__name__.lower()

        self.ajax_options = json.dumps({
            'replaceTarget': True,
            'url': context.route_url(self.route),
            'target': "div.{classname}-form-container".format(
                classname=self.classname),

        })

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
            'action': context.route_url(self.route),
        }

        bootstrap_form_style = getattr(self, 'bootstrap_form_style', None)
        if bootstrap_form_style is not None:
            self.form_options['bootstrap_form_style'] = bootstrap_form_style

    def appstruct(self):
        return self.schema.serialize(self.user)

    def get_template_context(self):
        return {
            'formname': self.classname
        }

    def failure(self, e):
        context = super(BaseFormView, self).failure(e)

        context.update(self.get_template_context())

        return context

    def show(self, form):
        context = super(BaseFormView, self).show(form)

        context.update(self.get_template_context())

        return context

    def full_page_reload(self):
        location = self.request.route_path(self.base_route)
        raise HTTPXRelocate(location)


class BaseActionsView(object):
    data_attribute = None
    verify_messages = {}
    default_verify_messages = {
        'ok': _('The data has been verified'),
        'error': _('Confirmation code is invalid'),
        'request': _('Check your email for further instructions'),
        'placeholder': _('Confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to you'),
        'expired': _('The confirmation code has expired. Please click on "Resend confirmation code" to get a new one'),
    }

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.user = context.user
        for msgid, msg in self.default_verify_messages.items():
            if msgid not in self.verify_messages:
                self.verify_messages[msgid] = msg

    def __call__(self):
        action = self.request.POST['action']
        action_method = getattr(self, '%s_action' % action)
        post_data = self.request.POST
        index = int(post_data['identifier'])
        result = action_method(index, post_data)
        result['action'] = action
        result['identifier'] = index
        return Response(json.dumps(result))

    def get_verification_data_id(self, data_to_verify):
        raise NotImplementedError()

    def verify_action(self, index, post_data):
        """ Common action to verificate some given data. You can override in subclasses """
        data_to_verify = self.user.get(self.data_attribute, [])[index]
        data_id = self.get_verification_data_id(data_to_verify)
        if 'code' in post_data:
            code_sent = post_data['code']
            verification_code = get_verification_code(self.request, self.data_attribute, data_id)
            if code_sent == verification_code['code']:
                if verification_code['expired']:
                    return {
                        'result': 'error',
                        'message': self.verify_messages['expired'],
                    }
                else:
                    verificate_code(self.request, self.data_attribute, code_sent)
                    return {
                        'result': 'ok',
                        'message': self.verify_messages['ok'],
                    }
            else:
                return {
                    'result': 'error',
                    'message': self.verify_messages['error'],
                }
        else:
            return {
                'result': 'getcode',
                'message': self.verify_messages['request'],
                'placeholder': self.verify_messages['placeholder'],
            }

    def resend_code_action(self, index, post_data):
        data = self.user.get(self.data_attribute, [])
        data_to_resend = data[index]
        data_id = self.get_verification_data_id(data_to_resend)
        code = new_verification_code(
            self.request, self.data_attribute, data_id,
            self.user, hasher=get_short_hash,
        )
        self.send_verification_code(data_id, code)

        msg = self.verify_messages['new_code_sent']
        msg = get_localizer(self.request).translate(msg)

        return {
            'result': 'ok',
            'message': msg,
        }

    def send_verification_code(self, data_id, code):
        raise NotImplementedError()


class HTTPXRelocate(HTTPOk):

    empty_body = True

    def __init__(self, new_location, **kwargs):
        super(HTTPXRelocate, self).__init__('', headers=[
            ('X-Relocate', new_location),
        ])
