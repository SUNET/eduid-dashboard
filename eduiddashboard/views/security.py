## Passwords form

from deform import Button
import json

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import get_localizer
from pyramid.renderers import render, render_to_response
from pyramid.view import view_config

from pyramid_deform import FormView
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduid_am.exceptions import UserDoesNotExist
from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import (Passwords, EmailResetPassword,
                                   NINResetPassword, ResetPasswordEnterCode,
                                   ResetPasswordStep2)
from eduiddashboard.vccs import add_credentials
from eduiddashboard.views import BaseFormView
from eduiddashboard.utils import flash, get_short_hash, generate_password


def change_password(request, user, old_password, new_password):
    """ Change the user password, deleting old credentials """
    vccs_url = request.registry.settings.get('vccs_url')
    added = add_credentials(vccs_url, old_password, new_password, user)
    if added:
        # do the save stuff
        request.db.profiles.save(user, safe=True)
        update_attributes.delay('eduid_dashboard', str(user['_id']))
    return added


def new_reset_password_code(request, user, mechanism='email'):
    hash_code = get_short_hash()
    request.db.reset_passwords.insert({
        'email': user['mail'],
        'hash_code': hash_code,
        'mechanism': mechanism,
        'verified': False,
    }, safe=True)
    reset_password_link = request.route_url(
        "reset-password-step2",
        code=hash_code,
    )
    return (hash_code, reset_password_link)


def send_reset_password_mail(request, email, user, code, reset_password_link):
    """ Send an email with the instructions for resetting password """
    mailer = get_mailer(request)

    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "email": email,
        "given_name": user.get('givenName', ''),
        "code": code,
        "reset_password_link": reset_password_link,
        "site_url": request.route_url("home"),
        "site_name": site_name,
    }

    message = Message(
        subject=_("Reset your password in {site_name}").format(
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


def send_reset_password_gov_message(request, nin, user, code, reset_password_link):
    """ Send an message to the gov mailbox with the instructions for resetting password """
    user_language = user.get('preferredLanguage', 'en')
    request.msgrelay.nin_reset_password(nin, code, reset_password_link, user_language)


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
        password_entropy = self.request.registry.settings.get('password_entropy', 60)
        if self.request.method == 'GET':
            self._password = generate_password(length=password_length,
                                               entropy=password_entropy)

            self._password = ' '.join([self._password[i*4: i*4+4]
                                       for i in range(0, len(self._password)/4)])

            self.request.session['last_generated_password'] = self._password

        elif self.request.method == 'POST':
            self._password = self.request.session.get('last_generated_password', generate_password(length=password_length))

        return self._password

    def save_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)

        if passwords_data.get('use_custom_password'):
            # The user has entered his own password and it was verified by
            # validators

            new_password = passwords_data.get('custom_password')

        else:
            # If the user has selected the suggested password, then it should
            # be in session
            new_password = self.get_suggested_password()

        old_password = passwords_data['old_password']
        user = self.request.session['user']
        # Load user from database to ensure we are working on an up-to-date set of credentials.
        # XXX this refresh is a bit redundant with the same thing being done in OldPasswordValidator.
        user = self.request.userdb.get_user_by_oid(user['_id'])

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


class BaseResetPasswordView(FormView):
    intro_message = None  # to override in subclasses

    def __init__(self, context, request):
        super(BaseResetPasswordView, self).__init__(request)

        self.classname = self.__class__.__name__.lower()

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
            'bootstrap_form_style': 'form-inline',
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
    intro_message = _('Forgot your password?')
    buttons = (Button('reset', title=_('Reset password'), css_class='btn-danger'), )

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        email_or_username = passwords_data['email_or_username']
        try:
            user = self.request.userdb.get_user_by_email(email_or_username)
        except UserDoesNotExist:
            user = self.request.userdb.get_user_by_username(email_or_username)
        code, reset_password_link = new_reset_password_code(self.request, user)
        email = user['mail']
        send_reset_password_mail(self.request, email, user, code, reset_password_link)
        msg = _('An email has been sent to your ${email} inbox.'
                'This email will contain instructions and a link '
                'that will let you reset your password.', mapping={
                  'email': email,
              })
        msg = get_localizer(self.request).translate(msg)

        flash(self.request, 'info', msg)
        return HTTPFound(location=self.request.route_url('reset-password-enter-code'))


@view_config(route_name='reset-password-mina', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordNINView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = NINResetPassword()
    route = 'reset-password-mina'
    intro_message = _('Forgot your password?')
    buttons = (Button('reset', title=_('Reset password'), css_class='btn-success'), )

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        email_or_username = passwords_data['email_or_username']
        try:
            user = self.request.userdb.get_user_by_email(email_or_username)
        except UserDoesNotExist:
            user = self.request.userdb.get_user_by_username(email_or_username)
        nin = None
        if user.get('norEduPersonNIN', False):
            nin = user['norEduPersonNIN'][-1]
        if nin is None:
            flash(self.request, 'info', _('Error: missing government mailbox '
                                          'for %s' % email_or_username))
            return HTTPFound(location=self.request.route_url('reset-password-mina'))
        code, reset_password_link = new_reset_password_code(self.request, user, mechanism='govmailbox')
        send_reset_password_gov_message(self.request, nin, user, code, reset_password_link)
        flash(self.request, 'info', _('An message has been sent to your government mailbox '
                                      'with the instructions to reset your password.'))
        return HTTPFound(location=self.request.route_url('reset-password-enter-code'))


@view_config(route_name='reset-password-enter-code', permission='edit',
             renderer='templates/reset-password-enter-code-form.jinja2')
class ResetPasswordEnterCodeView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = ResetPasswordEnterCode()
    route = 'reset-password-enter-code'
    intro_message = _('Enter your confirmation code')
    buttons = (Button('entercode', title=_('Enter code')), )

    def entercode_success(self, passwordform):
        reset_password_link = self.request.route_url(
            "reset-password-step2",
            code=passwordform['code'],
        )
        return HTTPFound(location=reset_password_link)


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
