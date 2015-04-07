import json
from copy import deepcopy
from bson import ObjectId

from pyramid.httpexceptions import HTTPOk, HTTPMethodNotAllowed
from pyramid.i18n import get_localizer
from pyramid.response import Response
from pyramid.renderers import render_to_response

from pyramid_deform import FormView

from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.forms import BaseForm
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import get_short_hash
from eduiddashboard.verifications import (get_verification_code,
                                          verify_code,
                                          new_verification_code)

from eduiddashboard import log

def get_dummy_status(request, user):
    return None


def sync_user(request, context, old_user):
    user = request.userdb.get_user_by_oid(old_user.get_id())
    user.retrieve_modified_ts(request.db.profiles)
    if context.workmode == 'personal':
        request.session['user'] = user
    else:
        request.session['edit-user'] = user
    return user


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
        self.response = request.response

        # Stop Internet Explorer from caching view fragments
        self.response.headers['Cache-Control'] = 'no-cache'

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
            'formname': self.classname,
        }

    def failure(self, e):
        rendered = e.field.widget.serialize(e.field, e.cstruct,
                                            request=self.request)
        context = {
            'form': rendered,
            }
        context.update(self.get_template_context())
        return context

    def show(self, form):
        appstruct = self.appstruct()
        if appstruct is None:
            rendered = form.render(request=self.request)
        else:
            rendered = form.render(appstruct, request=self.request)
        context = {
            'form': rendered,
            }
        context.update(self.get_template_context())
        return context

    def full_page_reload(self):
        location = self.request.route_path(self.base_route)
        raise HTTPXRelocate(location)

    def sync_user(self):
        self.user = sync_user(self.request, self.context, self.user)
        message = BaseActionsView.default_verify_messages['out_of_sync']
        self.request.session.flash(
                get_localizer(self.request).translate(message),
                queue='forms')


class BaseActionsView(object):
    data_attribute = None
    default_verify_messages = {
        'ok': _('The data has been verified'),
        'error': _('Confirmation code is invalid'),
        'request': _('Check your email for further instructions'),
        'placeholder': _('Confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to you'),
        'expired': _('The confirmation code has expired. Please click on '
                     '"Resend confirmation code" to get a new one'),
        'out_of_sync': _('The user was out of sync. Please try again.'),
    }

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.user = context.user
        self.verify_messages = {}
        for msgid, msg in self.default_verify_messages.items():
            if msgid not in self.special_verify_messages:
                self.verify_messages[msgid] = get_localizer(
                        request).translate(msg)
            else:
                self.verify_messages[msgid] = get_localizer(
                        request).translate(self.special_verify_messages[msgid])

    def __call__(self):
        action = self.request.POST['action']
        action_method = getattr(self, '%s_action' % action)
        post_data = self.request.POST
        try:
            index = int(post_data['identifier'])
        except ValueError:
            index = post_data['identifier']
        result = action_method(index, post_data)
        result['action'] = action
        result['identifier'] = index
        return Response(json.dumps(result))

    def get_verification_data_id(self, data_to_verify):
        raise NotImplementedError()

    def verify_action(self, index, post_data):
        """ Common action to verificate some given data.
            You can override in subclasses
        """
        data_to_verify = self.user.get(self.data_attribute, [])[index]
        data_id = self.get_verification_data_id(data_to_verify)
        return self._verify_action(data_id, post_data)

    def _verify_action(self, data_id, post_data):
        if 'code' in post_data:
            code_sent = post_data['code']
            verification_code = get_verification_code(self.request,
                                                      self.data_attribute,
                                                      obj_id=data_id,
                                                      code=code_sent,
                                                      user=self.user)
            if verification_code:
                if code_sent == verification_code['code']:
                    if verification_code['expired']:
                        log.debug("User {!r} verification code has expired".format(self.user))
                        return {
                            'result': 'error',
                            'message': self.verify_messages['expired'],
                        }
                    else:
                        try:
                            verify_code(self.request, self.data_attribute,
                                        code_sent)
                        except UserOutOfSync:
                            self.sync_user()
                            return {
                                'result': 'out_of_sync',
                                'message': self.verify_messages['out_of_sync'],
                            }
                    return {
                        'result': 'ok',
                        'message': self.verify_messages['ok'],
                        }
                else:
                    log.debug("Incorrect code for user {!r}: {!r}".format(self.user, code_sent))
            return {
                'result': 'error',
                'message': self.verify_messages['error'],
            }
        else:
            message = self.verify_messages['request'].format(data=data_id)
            return {
                'result': 'getcode',
                'message': message,
                'placeholder': self.verify_messages['placeholder'],
            }

    def resend_code_action(self, index, post_data):
        data = self.user.get(self.data_attribute, [])
        data_to_resend = data[index]
        data_id = self.get_verification_data_id(data_to_resend)
        reference, code = new_verification_code(
            self.request, self.data_attribute, data_id,
            self.user, hasher=get_short_hash,
        )
        self.send_verification_code(data_id, reference, code)
        msg = self.verify_messages['new_code_sent']
        return {
            'result': 'ok',
            'message': msg,
        }

    def send_verification_code(self, data_id, reference, code):
        raise NotImplementedError()

    def sync_user(self):
        self.user = sync_user(self.request, self.context, self.user)
        message = self.verify_messages['out_of_sync']
        return {
            'result': 'out_of_sync',
            'message': get_localizer(self.request).translate(message),
        }


class HTTPXRelocate(HTTPOk):

    empty_body = True

    def __init__(self, new_location, **kwargs):
        super(HTTPXRelocate, self).__init__('', headers=[
            ('X-Relocate', new_location),
            ('Content-Type', 'text/html; charset=UTF-8'),
        ])


class BaseWizard(object):

    collection_name = 'wizards'
    model = 'base'
    route = 'base'
    generic_filter = {
        'model': 'base',
    }
    last_step = 10
    datakey = None

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.user = context.user

        self.object_filter = {
            'userid': self.user.get_id(),
            'model': self.model
        }
        self.collection = request.db[self.collection_name]
        self.datakey = self.get_datakey()

        if self.datakey:
            self.object_filter['datakey'] = self.datakey

        self.obj = self.get_object()

    def get_datakey(self):
        if self.request.POST:
            return self.request.POST.get(self.model, None)
        elif self.request.GET:
            return self.request.GET.get(self.model, None)
        return None

    def get_object(self):

        obj = self.collection.find_one(self.object_filter)
        if not obj:
            obj = deepcopy(self.object_filter)
            obj.update({
                '_id': ObjectId(),
                'step': 0,
                'dismissed': False,
                'finished': False,
            })
        return obj

    def next_step(self):
        self.obj['finished'] = (self.obj['step'] == self.last_step)
        self.obj['step'] += 1
        self.collection.save(self.obj)

        return self.obj['step']

    def dismiss_wizard(self):
        if self.obj['step'] == 0:
            self.obj['dismissed'] = True
            obj_id = self.collection.save(self.obj)
            self.obj['_id'] = obj_id
        else:
            self.collection.update(self.object_filter, {'$set': {
                'dismissed': True
            }})
        message = _('The wizard was dismissed')
        return {
            'status': 'ok',
            'message': get_localizer(self.request).translate(message),
        }

    def is_open_wizard(self):
        return (not self.context.user.get(self.model) and
                not (self.obj['dismissed'] or self.obj['finished']))

    def __call__(self):
        if self.request.method == 'POST':
            return self.post()
        elif self.request.method == 'GET':
            return self.get()

        return HTTPMethodNotAllowed()

    def post(self):
        if self.request.POST['action'] == 'next_step':
            step = self.request.POST['step']
            action_method = getattr(self, 'step_%s' % step)
            post_data = self.request.POST
            response = action_method(post_data)

            if response and response['status'] == 'ok':
                self.next_step()

        elif self.request.POST['action'] == 'dismissed':
            response = self.dismiss_wizard()

        elif callable(getattr(self, self.request.POST['action'], None)):
            response = getattr(self, self.request.POST['action'])()

        else:
            message = _('Unexpected error')
            response = {
                'status': 'error',
                'text': get_localizer(self.request).translate(message),
            }

        return response

    def get_template_context(self):
        return {
            'user': self.user.get_doc(),
            'step': self.obj['step'],
            'path': self.request.route_path(self.route),
            'model': self.model,
            'datakey': self.datakey or '',
            'csrftoken': self.request.session.get_csrf_token(),
        }

    def get(self):
        template = 'eduiddashboard:templates/wizards/wizard-{0}.jinja2'.format(
            self.model)
        return render_to_response(template,
                                  self.get_template_context(),
                                  request=self.request)
