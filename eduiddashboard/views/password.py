## Passwords form

from deform import Button

from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render
from pyramid.view import view_config

from pyramid_deform import FormView
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import (Passwords, EmailResetPassword,
                                   NINResetPassword, ResetPasswordStep2)
from eduiddashboard.vccs import add_credentials
from eduiddashboard.views import BaseFormView
from eduiddashboard.utils import flash, get_unique_hash


def change_password(request, user, old_password, new_password):
    """ Change the user password, deleting old credentials """
    vccs_url = request.registry.settings.get('vccs_url')
    added = add_credentials(vccs_url, old_password, new_password, user)
    if added:
        # do the save staff
        request.db.profiles.save(user, safe=True)
        update_attributes.delay('eduid_dashboard', str(user['_id']))
    return added


def new_reset_password_code(request, user, mechanism='email'):
    hash_code = get_unique_hash()
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
    return reset_password_link


def send_reset_password_mail(request, email, user, reset_password_link):
    """ Send an email with the instructions for resetting password """
    mailer = get_mailer(request)

    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "email": email,
        "given_name": user.get('givenName', ''),
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


def send_reset_password_gov_message(request, nin, user, reset_password_link):
    """ Send an message to the gov mailbox with the instructions for resetting password """
    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "nin": nin,
        "given_name": user.get('givenName', ''),
        "reset_password_link": reset_password_link,
        "site_url": request.route_url("home"),
        "site_name": site_name,
    }
    print context  # TODO: Implement the eduid_msg communication


@view_config(route_name='passwords', permission='edit',
             renderer='templates/passwords-form.jinja2')
class PasswordsView(BaseFormView):
    """
    Change user passwords
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Passwords()
    route = 'passwords'

    def save_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        new_password = passwords_data['new_password']
        old_password = passwords_data['old_password']

        # adding new credentials
        user = self.request.session['user']

        ok = change_password(self.request, user, old_password, new_password)
        if ok:
            self.request.session.flash(_('Your password has been successfully updated'),
                                       queue='forms')
        else:
            self.request.session.flash(_('An error has occured while updating your password, '
                                         'please try again or contact support if the problem persists.'),
                                       queue='forms')


class BaseResetPasswordView(FormView):
    intro_message = None  # to override in subclasses

    def __init__(self, context, request):
        super(BaseResetPasswordView, self).__init__(request)

        self.classname = self.__class__.__name__.lower()

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
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
        email = passwords_data['email']
        user = self.request.userdb.get_user_by_email(email)
        reset_password_link = new_reset_password_code(self.request, user)
        send_reset_password_mail(self.request, email, user, reset_password_link)
        flash(self.request, 'info', _('An email has been sent to the address you entered.'
                                      'This email will contain instructions and a link'
                                      'that will let you reset your password.'))
        return {
            'message': _('Please read the email sent to you for further instructions. This window can now safely be closed.'),
        }


@view_config(route_name='reset-password-nin', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordNINView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = NINResetPassword()
    route = 'reset-password-nin'
    intro_message = _('Forgot your password?')
    buttons = (Button('reset', title=_('Reset password'), css_class='btn-success'), )

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        nin = passwords_data['norEduPersonNIN']
        user = self.request.userdb.get_user_by_nin(nin)
        reset_password_link = new_reset_password_code(self.request, user, mechanism='govmailbox')
        send_reset_password_gov_message(self.request, nin, user, reset_password_link)
        flash(self.request, 'info', _('An message has been sent to your government mailbox'
                                      'with the instructions to reset your password.'))
        return {
            'message': _('Now you can follow the instructions and close this window safely.'),
        }


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
            return HTTPNotFound()
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
            flash(self.request, 'info', _('An error has occured while updating your password,'
                                          'please try again or contact support if the problem persists.'))
        return {
            'message': _('You can now log in by <a href="${homelink}">clicking here</a>',
                         mapping={'homelink': self.request.route_url('profile-editor')}),
        }
