## Passwords form

from deform import Button
import json

from datetime import datetime, timedelta
from bson import ObjectId
import pytz

from pyramid.httpexceptions import HTTPFound, HTTPBadRequest, HTTPUnauthorized
from pyramid.view import view_config
from pyramid.i18n import get_localizer

from pyramid_deform import FormView
from pyramid.renderers import render_to_response

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import (Passwords, EmailResetPassword,
                                   NINResetPassword,
                                   ResetPasswordStep2)
from eduiddashboard.vccs import add_credentials
from eduiddashboard.views import BaseFormView
from eduiddashboard.emails import send_reset_password_mail
from eduiddashboard.saml2.acs_actions import acs_action, schedule_action
from eduiddashboard.saml2.views import get_authn_request
from eduiddashboard.saml2.utils import get_location
from eduiddashboard.utils import generate_password, get_unique_hash, validate_email_format, normalize_email, \
    convert_to_localtime, normalize_to_e_164
from eduiddashboard import log


def change_password(request, user, old_password, new_password):
    """ Change the user password, deleting old credentials """
    vccs_url = request.registry.settings.get('vccs_url')
    added = add_credentials(vccs_url, old_password, new_password, user)
    if added:
        user.set_terminated(terminate=False)
        update_doc = {'$set': {'passwords': user.get_passwords(),
                               'terminated': None}}
        user.save(request, check_sync=False, update_doc=update_doc)
    return added


def new_reset_password_code(request, user, mechanism='email'):
    hash_code = get_unique_hash()
    date = datetime.now(pytz.utc)
    request.db.reset_passwords.remove({
        'email': user.get_mail()
    })
    reference = request.db.reset_passwords.insert({
        'email': user.get_mail(),
        'hash_code': hash_code,
        'mechanism': mechanism,
        'created_at': date,
    }, safe=True, manipulate=True)
    log.debug("New reset password code: {!s} via {!s} for user: {!r}.".format(hash_code, mechanism, user))
    reset_password_link = request.route_url(
        "reset-password-step2",
        code=hash_code,
    )
    return reference, reset_password_link


def send_reset_password_gov_message(request, reference, nin, user, reset_password_link):
    """ Send an message to the gov mailbox with the instructions for resetting password """
    user_language = user.get_preferred_language()
    email = user.get_mail()
    password_reset_timeout = int(request.registry.settings.get("password_reset_timeout", "120")) / 60
    request.msgrelay.nin_reset_password(reference, nin, email, reset_password_link, password_reset_timeout,
                                        user_language)


def generate_suggested_password(request):
    """
    The suggested password is saved in session to avoid form hijacking
    """
    password_length = request.registry.settings.get('password_length', 12)

    if request.method == 'GET':
        password = generate_password(length=password_length)
        password = ' '.join([password[i*4: i*4+4] for i in range(0, len(password)/4)])

        request.session['last_generated_password'] = password

    elif request.method == 'POST':
        password = request.session.get('last_generated_password', generate_password(length=password_length))

    return password


def get_authn_info(request):
    """
    Get credential information for the current user.

    :param request: the request object
    :return: a list of dicts [{'type': string, 'created_ts': timestamp, 'success_ts': timestamp }]
    """
    if 'edit-user' in request.session:
        user = request.session['edit-user']
    else:
        user = request.session['user']

    authninfo = []

    for credential in user.get_passwords():
        auth_entry = request.authninfodb.authn_info.find_one({'_id': ObjectId(credential['id'])})
        log.debug("cred id: {!r} auth entry: {!r}".format(credential['id'], auth_entry))
        if auth_entry:
            created_dt = convert_to_localtime(credential['created_ts'])
            success_dt = convert_to_localtime(auth_entry['success_ts'])
            data_type = _('Password')
            data = {'type': get_localizer(request).translate(data_type),
                    'created_ts': created_dt.strftime('%Y-%b-%d %H:%M'),
                    'success_ts': success_dt.strftime('%Y-%b-%d %H:%M')}
            authninfo.append(data)

    return authninfo


@view_config(route_name='start-password-change',
             request_method='POST',
             permission='edit')
def start_password_change(context, request):
    '''
    '''
    settings = request.registry.settings

    # check csrf
    csrf = request.POST.get('csrf')
    if csrf != request.session.get_csrf_token():
        return HTTPBadRequest()

    selected_idp = request.session.get('selected_idp')
    relay_state = context.route_url('profile-editor')
    loa = context.get_loa()
    info = get_authn_request(request, relay_state, selected_idp,
                             required_loa=loa, force_authn=True)
    schedule_action(request.session, 'change-password-action')

    return HTTPFound(location=get_location(info))


@acs_action('change-password-action')
def change_password_action(request, session_info, user):
    settings = request.registry.settings
    logged_user = request.session['user']

    if logged_user.get_id() != user.get_id():
        raise HTTPUnauthorized("Wrong user")

    # set timestamp in session
    request.session['re-authn-ts'] = datetime.utcnow()
    # send to password change form
    return HTTPFound(request.route_url('password-change'))


@view_config(route_name='security',
             permission='edit',
             renderer='eduiddashboard:templates/passwords-form.jinja2')
def security_view(context, request):
    return {
        'formname': 'security',
        'authninfo': get_authn_info(request)
    }


@view_config(route_name='password-change',
             permission='edit')
class PasswordsView(BaseFormView):
    """
    Change user passwords
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Passwords()
    base_route = 'password-change'
    route = 'password-change'
    buttons = (Button(name='save', title=_('Change password')), )

    use_ajax = False
    _password = None

    def __init__(self, context, request):
        super(PasswordsView, self).__init__(context, request)

        self.ajax_options = json.dumps({
            'replaceTarget': False,
            'url': context.route_url(self.route),
            'target': "#changePasswordDialog",
        })

    def appstruct(self):
        passwords_dict = {
            'suggested_password': self.get_suggested_password()
        }
        return self.schema.serialize(passwords_dict)

    def __call__(self):
        if self.request.method == 'POST':
            self.request.POST.add('suggested_password', self.get_suggested_password())
        result = super(PasswordsView, self).__call__()
        template = 'eduiddashboard:templates/passwords-form-dialog.jinja2'
        return render_to_response(template, result, request=self.request)

    def get_template_context(self):
        context = super(PasswordsView, self).get_template_context()

        context.update({
            'message': getattr(self, 'message', ''),
            'changed': getattr(self, 'changed', False),
            'authninfo': get_authn_info(self.request)
        })
        return context

    def get_suggested_password(self):
        """
        The suggested password is saved in session to avoid form hijacking
        """
        if self._password is None:
            self._password = generate_suggested_password(self.request)
        return self._password

    def save_success(self, passwordform):
        authn_ts = self.request.session.get('re-authn-ts', None)
        if authn_ts is None:
            raise HTTPBadRequest(_('No authentication info'))
        else:
            now = datetime.utcnow()
            delta = now - authn_ts
            if int(delta.total_seconds()) > 600:
                msg = _('Stale authentication info. Please try again.')
                self.request.session.flash('error|' + msg)
                raise HTTPFound(self.context.route_url('profile-editor'))
        del self.request.session['re-authn-ts']
        passwords_data = self.schema.serialize(passwordform)
        if 'edit-user' in self.request.session:
            user = self.request.session['edit-user']
        else:
            user = self.request.session['user']

        if passwords_data.get('use_custom_password') == 'true':
            # The user has entered his own password and it was verified by
            # validators
            log.debug("Password change for user {!r} (custom password).".format(user.get_id()))
            new_password = passwords_data.get('custom_password')

        else:
            # If the user has selected the suggested password, then it should
            # be in session
            log.debug("Password change for user {!r} (suggested password).".format(user.get_id()))
            new_password = self.get_suggested_password()

        new_password = new_password.replace(' ', '')

        old_password = passwords_data['old_password']

        # Load user from database to ensure we are working on an up-to-date set of credentials.
        # XXX this refresh is a bit redundant with the same thing being done in OldPasswordValidator.
        user = self.request.userdb.get_user_by_oid(user.get_id())
        user.retrieve_modified_ts(self.request.db.profiles)

        self.changed = change_password(self.request, user, old_password, new_password)
        if self.changed:
            message = 'success|' + _('Your password has been successfully updated')
        else:
            message = 'error|' + _('An error has occured while updating your password, '
                        'please try again or contact support if the problem persists.')
        self.request.session.flash(message)
        raise HTTPFound(self.context.route_url('profile-editor'))


@view_config(route_name='reset-password', renderer='templates/reset-password.jinja2',
             request_method='GET', permission='edit')
def reset_password(context, request):
    """ Reset password """
    return {
    }


@view_config(route_name='reset-password-expired', renderer='templates/reset-password-expired.jinja2',
             request_method='GET', permission='edit')
def reset_password_expired(context, request):
    """ Reset password - expired token"""
    return {
    }


@view_config(route_name='reset-password-sent', permission='edit',
             request_method='GET', renderer='templates/reset-password-sent.jinja2')
def reset_password_sent(context, request):
    """
    Reset password sent confirmation view.
    """
    if '_reset_type' in request.session:
        type = request.session['_reset_type']
        request.session.invalidate()
        return {
            'type': type,
            'login_url': request.route_url('saml2-login'),
        }

    return HTTPFound(location=request.route_url('reset-password'))


class BaseResetPasswordView(FormView):
    intro_message = _("Please enter e-mail address, national identity number or phone number "
                      "associated with your eduID account, "
                      "and we'll send you a link to reset your password.")

    def __init__(self, context, request):
        super(BaseResetPasswordView, self).__init__(request)

        self.classname = self.__class__.__name__.lower()

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
            'bootstrap_form_style': 'form-horizontal',
        }

    def get_template_context(self):
        return {
            'intro_message': self.intro_message
        }

    def failure(self, e):
        context = super(BaseResetPasswordView, self).failure(e)
        context.update(self.get_template_context())
        return context

    def show(self, form):
        context = super(BaseResetPasswordView, self).show(form)
        context.update(self.get_template_context())
        return context

    def _search_user(self, text):
        """
        Find a user matching email, mobile or NIN.

        @param text: search string
        @return: user object
        """
        if validate_email_format(text):
            user = self.request.userdb.get_user_by_email(normalize_email(text))
        elif text.startswith(u'0') or text.startswith(u'+'):
            text = normalize_to_e_164(self.request, text)
            user = self.request.userdb.get_user_by_filter(
                {'mobile': {'$elemMatch': {'mobile': text, 'verified': True}}}
            )
        else:
            user = self.request.userdb.get_user_by_nin(text)

        user.retrieve_modified_ts(self.request.db.profiles)
        log.debug("Found user {!r} using input {!s}.".format(user, text))
        return user


@view_config(route_name='reset-password-email', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordEmailView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = EmailResetPassword()
    route = 'reset-password-email'
    buttons = (
        Button('reset', title=_('Reset password'), css_class='btn-danger'),
        Button('cancel', _('Cancel')),
    )

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        email_or_username = passwords_data['email_or_username']

        try:
            user = self._search_user(email_or_username)
            log.debug("Reset password via email initiated for user {!r}".format(user))
            self.request.stats.count('dashboard/pwreset_email_init', 1)
        except self.request.userdb.exceptions.UserDoesNotExist:
            log.debug("Tried to initiate reset password via email but user {!r} does not exist".format(
                email_or_username))
            self.request.stats.count('dashboard/pwreset_email_init_unknown_user', 1)
            user = None

        if user is not None:
            reference, reset_password_link = new_reset_password_code(self.request, user)
            send_reset_password_mail(self.request, user, reset_password_link)

        self.request.session['_reset_type'] = _('email')
        return HTTPFound(location=self.request.route_url('reset-password-sent'))

    def cancel_success(self, passwordform):
        return HTTPFound(location=self.request.route_url('saml2-login'))
    cancel_failure = cancel_success


@view_config(route_name='reset-password-mina', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordNINView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = NINResetPassword()
    route = 'reset-password-mina'
    buttons = (
        Button('reset', title=_('Reset password'), css_class='btn-success'),
        Button('cancel', _('Cancel')),
    )

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        email_or_username = passwords_data['email_or_username']

        try:
            user = self._search_user(email_or_username)
            log.debug("Reset password via mm initiated for user {!r}.".format(user))
            self.request.stats.count('dashboard/pwreset_mm_init', 1)
        except self.request.userdb.exceptions.UserDoesNotExist:
            log.debug("Tried to initiate reset password via mm but user {!r} does not exist".format(email_or_username))
            self.request.stats.count('dashboard/pwreset_mm_init_unknown_user', 1)
            user = None

        if user is not None:
            nin = None
            nins = user.get_nins()
            if nins:
                nin = nins[-1]
            if nin is not None:
                reference, reset_password_link = new_reset_password_code(self.request, user, mechanism='govmailbox')
                send_reset_password_gov_message(self.request, reference, nin, user, reset_password_link)

        self.request.session['_reset_type'] = _('Myndighetspost')
        return HTTPFound(location=self.request.route_url('reset-password-sent'))

    def cancel_success(self, passwordform):
        return HTTPFound(location=self.request.route_url('saml2-login'))
    cancel_failure = cancel_success


@view_config(route_name='reset-password-step2', permission='edit',
             renderer='templates/reset-password-form2.jinja2')
class ResetPasswordStep2View(BaseResetPasswordView):
    """
    Form to finish user password reset.
    """

    schema = ResetPasswordStep2()
    route = 'reset-password-step2'
    buttons = (
        Button('reset', title=_('Change password'), css_class='btn-success'),
        Button('cancel', _('Cancel')),
    )
    intro_message = _('Please choose a new password for your eduID account.')

    def __init__(self, context, request):
        super(ResetPasswordStep2View, self).__init__(context, request)
        self._password = None

    def appstruct(self):
        passwords_dict = {
            'suggested_password': self.get_suggested_password()
        }
        return self.schema.serialize(passwords_dict)

    def __call__(self):
        hash_code = self.request.matchdict['code']
        password_reset = self.request.db.reset_passwords.find_one({'hash_code': hash_code})

        if password_reset is None:
            self.request.stats.count('dashboard/pwreset_code_not_found', 1)
            return HTTPFound(self.request.route_path('reset-password-expired'))

        date = datetime.now(pytz.utc)
        reset_timeout = int(self.request.registry.settings['password_reset_timeout'])
        reset_date = password_reset['created_at'] + timedelta(minutes=reset_timeout)
        if reset_date < date:
            self.request.db.reset_passwords.remove({'_id': password_reset['_id']})
            self.request.stats.count('dashboard/pwreset_code_expired', 1)
            return HTTPFound(self.request.route_path('reset-password-expired'))

        return super(ResetPasswordStep2View, self).__call__()

    def get_suggested_password(self):
        """
        The suggested password is saved in session to avoid form hijacking
        """
        if self._password is None:
            self._password = generate_suggested_password(self.request)
        return self._password

    def reset_success(self, passwordform):
        form_data = self.schema.serialize(passwordform)
        hash_code = self.request.matchdict['code']
        password_reset = self.request.db.reset_passwords.find_one({'hash_code': hash_code})
        user = self.request.userdb.get_user_by_email(password_reset['email'])
        user.retrieve_modified_ts(self.request.db.profiles)

        if form_data.get('use_custom_password') == 'true':
            log.debug("Password change for user {!r} (custom password).".format(user.get_id()))
            new_password = form_data.get('custom_password')
            self.request.stats.count('dashboard/pwreset_custom_password', 1)
        else:
            log.debug("Password change for user {!r} (suggested password).".format(user.get_id()))
            new_password = self.get_suggested_password()
            self.request.stats.count('dashboard/pwreset_generated_password', 1)

        new_password = new_password.replace(' ', '')

        self.request.db.reset_passwords.remove({'_id': password_reset['_id']})
        ok = change_password(self.request, user, '', new_password)

        if ok:
            self.request.stats.count('dashboard/pwreset_changed_password', 1)
            if password_reset['mechanism'] == 'email':
                # TODO: Re-send verification code in advance?
                nins = user.get_nins()
                reset_nin_count = 0
                if nins:
                    # XXX shouldn't the downgrade of NIN to unverified be done to *ALL* the user's NINs?
                    nin = nins[-1]
                    if nin is not None:
                        self.request.db.profiles.update({
                            "_id": user.get_id()
                        }, {
                            "$set": {"norEduPersonNIN": []}
                        })
                        # Do not remove the verification as we no longer allow users to remove a already verified nin
                        # even if it gets unverified by a e-mail password reset.
                        self.request.db.verifications.update({
                            "user_oid": user.get_id(),
                            "model_name": "norEduPersonNIN",
                            "obj_id": nin
                        }, {
                            "$set": {"verified": False}
                        })
                        update_attributes('eduid_dashboard', str(user['_id']))
                        reset_nin_count += 1
                    self.request.stats.count('dashboard/pwreset_downgraded_NINs', reset_nin_count)
            url = self.request.route_url('profile-editor')
            reset = True
        else:
            self.request.stats.count('dashboard/pwreset_password_change_failed', 1)
            url = self.request.route_url('reset-password')
            reset = False
        return {
            'url': url,
            'reset': reset
        }

    def cancel_success(self, passwordform):
        return HTTPFound(location=self.request.route_url('saml2-login'))
    cancel_failure = cancel_success
