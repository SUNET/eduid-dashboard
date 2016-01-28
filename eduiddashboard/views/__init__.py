import json
from copy import deepcopy
from bson import ObjectId

from pyramid.httpexceptions import (HTTPOk,
                                    HTTPMethodNotAllowed,
                                    HTTPBadRequest)
from pyramid.i18n import get_localizer
from pyramid.response import Response
from pyramid.renderers import render_to_response

from pyramid_deform import FormView
from eduid_userdb.dashboard import DashboardUser

from eduid_userdb.exceptions import UserOutOfSync

from eduiddashboard.forms import BaseForm
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import (get_short_hash,
                                  sanitize_get,
                                  sanitize_post_key,
                                  sanitize_post_multidict,
                                  retrieve_modified_ts)
from eduiddashboard.verifications import (get_verification_code,
                                          verify_code,
                                          new_verification_code)
from eduiddashboard import log
from eduiddashboard.session import store_session_user


def get_dummy_status(request, user):
    return None


def sync_user(request, context, old_user):
    user = request.userdb.get_user_by_id(old_user.user_id)

    if isinstance(user, DashboardUser):
        retrieve_modified_ts(user, request.dashboard_userdb)
    else:
        user.retrieve_modified_ts(request.db.profiles)

    if context.workmode == 'personal':
        store_session_user(request, user)
    else:
        store_session_user(request, user, edit_user = True)
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
        return self.schema.serialize(self.user.to_dict())

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
        'success': _('The data has been verified'),
        'error': _('Confirmation code is invalid'),
        'request': _('Check your email for further instructions'),
        'placeholder': _('Confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to you'),
        'expired': _('The confirmation code has expired. Please click on '
                     '"Resend confirmation code" to get a new one'),
        'out_of_sync': _('Your user profile is out of sync. Please '
                         'reload the page and try again.'),
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
        action = sanitize_post_multidict(self.request, 'action')
        post_data = self.request.POST
        try:
            index = int(post_data['identifier'])
        except ValueError:
            index = post_data['identifier']

        # The if-clause below functions as a form of whitelisting.
        if action == 'verify':
            result = self.verify_action(index, post_data)
        elif action == 'resend_code':
            result = self.resend_code_action(index, post_data)
        elif action == 'setprimary':
            result = self.setprimary_action(index, post_data)
        elif action == 'remove':
            result = self.remove_action(index, post_data)
        elif action == 'verify_mb':
            result = self.verify_mb_action(index, post_data)
        elif action == 'verify_lp':
            result = self.verify_lp_action(index, post_data)
        elif action == 'send_letter':
            result = self.send_letter_action(index, post_data)
        elif action == 'finish_letter':
            result = self.finish_letter_action(index, post_data)
        else:
            raise HTTPBadRequest("Unsupported action")

        result['action'] = action
        result['identifier'] = index
        return Response(json.dumps(result))

    def get_verification_data_id(self, data_to_verify):
        raise NotImplementedError()

    def verify_action(self, index, post_data):
        """ Common action to verify some given data.
            You can override in subclasses
        """

        # Catch the unlikely event when the user have e.g. removed all entries
        # in a separate tab, or one in the middle and then tries to resend the
        # code for a non-existing entry.
        # This is an incomplete fix since it is better if we can get the list
        # from the UI and then check that the entry which the client want to
        # resend the code for corresponds to the same entry we get from
        # data[index].
        try:
            _data = self.user.get(self.data_attribute, [])
            data_to_verify = _data[index]
        except IndexError:
            log.warning('Index error in verify_action, user {!s}'.format(self.user))
            message = self.verify_messages['out_of_sync']
            return {
                'result': 'out_of_sync',
                'message': get_localizer(self.request).translate(message),
            }

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
                        'result': 'success',
                        'message': self.verify_messages['success'],
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

        # Catch the unlikely event when the user have e.g. removed all entries
        # in a separate tab, or one in the middle and then tries to resend the
        # code for a non-existing entry.
        # This is an incomplete fix since it is better if we can get the list
        # from the UI and then check that the entry which the client want to
        # resend the code for corresponds to the same entry we get from
        # data[index].
        try:
            data_to_resend = data[index]
        except IndexError:
            log.warning('Index error in resend_code_action, user {!s}'.format(self.user))
            message = self.verify_messages['out_of_sync']
            return {
                'result': 'out_of_sync',
                'message': get_localizer(self.request).translate(message),
            }

        data_id = self.get_verification_data_id(data_to_resend)
        reference, code = new_verification_code(
            self.request, self.data_attribute, data_id,
            self.user, hasher=get_short_hash,
        )
        self.send_verification_code(data_id, reference, code)
        msg = self.verify_messages['new_code_sent']
        return {
            'result': 'success',
            'message': msg,
        }

    def send_verification_code(self, data_id, reference, code):
        raise NotImplementedError()

    def sync_user(self):
        log.warning('User {!s} could not be saved (views/__init__.py)'.format(self.user))
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
        try:
            userid = self.user.get_id()
        except AttributeError:
            userid = self.user.user_id

        self.object_filter = {
            'userid': userid,
            'model': self.model
        }
        self.collection = request.db[self.collection_name]
        self.datakey = self.get_datakey()

        if self.datakey:
            self.object_filter['datakey'] = self.datakey

        self.obj = self.get_object()

    def get_datakey(self):
        if self.request.POST:
            return sanitize_post_key(self.request, self.model, None)
        elif self.request.GET:
            return sanitize_get(self.request, self.model, None)
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
            'status': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def is_open_wizard(self):
        attr = self.model
        if attr == 'norEduPersonNIN':
            attr = 'nins'
        objs = getattr(self.context.user, attr).to_list()
        return (not objs and
                not (self.obj['dismissed'] or self.obj['finished']))

    def __call__(self):
        if self.request.method == 'POST':
            return self.post()
        elif self.request.method == 'GET':
            return self.get()

        return HTTPMethodNotAllowed()

    def post(self):
        if sanitize_post_multidict(self.request, 'action') == 'next_step':
            step = sanitize_post_multidict(self.request, 'step')
            post_data = self.request.POST

            # The if-clause below functions as a form of whitelisting.
            if step == '0':
                response = self.step_0(post_data)
            elif step == '1':
                response = self.step_1(post_data)
            else:
                raise HTTPBadRequest("Unsupported wizard step")

            if response and response['status'] == 'success':
                self.next_step()

        elif sanitize_post_multidict(self.request, 'action') == 'dismissed':
            response = self.dismiss_wizard()

        elif sanitize_post_multidict(self.request, 'action') == 'resendcode':
            response = self.resendcode()

        else:
            message = _('Unexpected error')
            response = {
                'status': 'error',
                'text': get_localizer(self.request).translate(message),
            }

        return response

    def get_template_context(self):
        return {
            # seems to not be used in the wizard jinja files -- ft@ 2016-01-15 'user': self.user.get_doc(),
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
