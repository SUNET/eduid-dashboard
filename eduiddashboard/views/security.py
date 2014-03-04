## Passwords form

from deform import Button
import json

from datetime import datetime
from time import time

from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render, render_to_response
from pyramid.view import view_config

from pyramid_deform import FormView
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import (Passwords, EmailResetPassword,
                                   NINResetPassword, ResetPasswordEnterCode,
                                   ResetPasswordStep2)
from eduiddashboard.vccs import add_credentials
from eduiddashboard.views import BaseFormView
from eduiddashboard.utils import flash, generate_password, get_unique_hash
from eduiddashboard import log


def change_password(request, user, old_password, new_password):
    """ Change the user password, deleting old credentials """
    vccs_url = request.registry.settings.get('vccs_url')
    added = add_credentials(vccs_url, old_password, new_password, user)
    if added:
        user.save(request)
    return added


def new_reset_password_code(request, user, mechanism='email'):
    hash_code = get_unique_hash()
    date = datetime.fromtimestamp(time(), None)
    request.db.reset_passwords.insert({
        'email': user.get_mail(),
        'hash_code': hash_code,
        'mechanism': mechanism,
        'verified': False,
        'created_at': date,
    }, safe=True)
    reset_password_link = request.route_url(
        "reset-password-step2",
        code=hash_code,
    )
    return reset_password_link


def send_reset_password_mail(request, user, reset_password_link):
    """ Send an email with the instructions for resetting password """
    mailer = get_mailer(request)

    site_name = request.registry.settings.get("site.name", "eduID")
    password_reset_timeout = int(request.registry.settings.get("password_reset_timeout", "120")) / 60
    email = user.get_mail()

    context = {
        "email": email,
        "reset_password_link": reset_password_link,
        "password_reset_timeout": password_reset_timeout,
        "site_url": request.route_url("home"),
        "site_name": site_name,
    }

    message = Message(
        subject=_("Reset your {site_name} password").format(
            site_name=site_name),
        sender=request.registry.settings.get("mail.default_sender"),
        recipients=[email],
        body=render(
            "templates/reset-password-email.txt.jinja2",
            context,
            request,
        ),
        html=render(
            "templates/reset-password-email.html.jinja2",
            context,
            request,
        ),
    )
    mailer.send(message)


def send_reset_password_gov_message(request, nin, user, reset_password_link):
    """ Send an message to the gov mailbox with the instructions for resetting password """
    user_language = user.get_preferred_language()
    email = user.get_mail()
    password_reset_timeout = int(request.registry.settings.get("password_reset_timeout", "120")) / 60
    request.msgrelay.nin_reset_password(nin, email, reset_password_link, password_reset_timeout, user_language)


@view_config(route_name='security', permission='edit')
class PasswordsView(BaseFormView):
    """
    Change user passwords
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Passwords()
    route = 'security'
    buttons = (Button(name='save', title=_('Change password')), )
    _password = None

    def __init__(self, context, request):
        super(PasswordsView, self).__init__(context, request)

        self.ajax_options = json.dumps({
            'replaceTarget': False,
            'url': context.route_url(self.route),
            'target': "#changePasswordDialog .modal-body",
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

        if self.request.method == 'POST':
            template = 'eduiddashboard:templates/passwords-form-dialog.jinja2'
        else:
            template = 'eduiddashboard:templates/passwords-form.jinja2'
        return render_to_response(template, result, request=self.request)

    def get_template_context(self):
        context = super(PasswordsView, self).get_template_context()
        context.update({
            'message': getattr(self, 'message', ''),
            'changed': getattr(self, 'changed', False),
        })
        return context

    def get_suggested_password(self):
        """
            The suggested password is saved in session to avoid form hijacking
        """
        if self._password is not None:
            return self._password
        password_length = self.request.registry.settings.get('password_length', 12)

        if self.request.method == 'GET':
            self._password = generate_password(length=password_length)
            self._password = ' '.join([self._password[i*4: i*4+4]
                                       for i in range(0, len(self._password)/4)])

            self.request.session['last_generated_password'] = self._password

        elif self.request.method == 'POST':
            self._password = self.request.session.get('last_generated_password', generate_password(length=password_length))

        return self._password

    def save_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
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

        self.changed = change_password(self.request, user, old_password, new_password)
        if self.changed:
            self.message = _('Your password has been successfully updated')
        else:
            self.message = _('An error has occured while updating your password, '
                             'please try again or contact support if the problem persists.')


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
    SEARCH_FIELDS = [
        'mailAliases.email',
        'mobile.mobile',
        'norEduPersonNIN',
    ]
    intro_message = _("Enter an email address, social security number or phone number "
                      "associated with your eduID account, "
                      "and we'll send you a link to reset your password.")

    def __init__(self, context, request):
        super(BaseResetPasswordView, self).__init__(request)

        self.classname = self.__class__.__name__.lower()

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
            'bootstrap_form_style': 'form-vertical',
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
            filter_dict = {'$or': []}
            for field in self.SEARCH_FIELDS:
                filter_dict['$or'].append({field: email_or_username})

            user = self.request.userdb.get_user_by_filter(filter_dict)
        except self.request.userdb.exceptions.UserDoesNotExist:
            log.debug("User {!r} does not exist".format(email_or_username))
            user = None

        if user is not None:
            reset_password_link = new_reset_password_code(self.request, user)
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
            filter_dict = {'$or': []}
            for field in self.SEARCH_FIELDS:
                filter_dict['$or'].append({field: email_or_username})

            user = self.request.userdb.get_user_by_filter(filter_dict)
        except self.request.userdb.exceptions.UserDoesNotExist:
            log.debug("User {!r} does not exist".format(email_or_username))
            user = None

        if user is not None:
            nin = None
            nins = user.get_nins()
            if nins:
                nin = nins[-1]
            if nin is not None:
                reset_password_link = new_reset_password_code(self.request, user, mechanism='govmailbox')
                send_reset_password_gov_message(self.request, nin, user, reset_password_link)

        self.request.session['_reset_type'] = _('Myndighetspost')
        return HTTPFound(location=self.request.route_url('reset-password-sent'))

    def cancel_success(self, passwordform):
        return HTTPFound(location=self.request.route_url('saml2-login'))
    cancel_failure = cancel_success


@view_config(route_name='reset-password-step2', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordStep2View(BaseResetPasswordView):
    """
    Form to finish user password reset.
    """

    schema = ResetPasswordStep2()
    route = 'reset-password-step2'
    buttons = ('reset', )
    intro_message = _('Complete your password reset')

    def __call__(self):
        hash_code = self.request.matchdict['code']
        reset_passwords = self.request.db.reset_passwords.find({'hash_code': hash_code})
        if reset_passwords.count() == 0:
            flash(self.request, 'error', _('Invalid code.'))
            return HTTPFound(self.request.route_path('reset-password-expired'))
        return super(ResetPasswordStep2View, self).__call__()

    def reset_success(self, passwordform):
        hash_code = self.request.matchdict['code']
        reset_password = self.request.db.reset_passwords.find({'hash_code': hash_code})[0]
        user = self.request.userdb.get_user_by_email(reset_password['email'])

        new_password = passwordform['new_password']
        ok = change_password(self.request, user, '', new_password)
        if ok:
            if reset_password['mechanism'] == 'email':
                pass  # TODO: reset the user LOA
            self.request.db.reset_passwords.remove({'_id': reset_password['_id']})
            flash(self.request, 'info', _('Password has been reset successfully'))
        else:
            flash(self.request, 'info', _('An error has occurred while updating your password, '
                                          'please try again or contact support if the problem persists.'))
        return {
            'message': _('You can now log in by <a href="${homelink}">clicking here</a>',
                         mapping={'homelink': self.request.route_url('profile-editor')}),
        }
