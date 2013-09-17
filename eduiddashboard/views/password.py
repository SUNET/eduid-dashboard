## Passwords form

import uuid
from md5 import md5

from pyramid.renderers import render
from pyramid.view import view_config

from pyramid_deform import FormView
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduid_am.exceptions import UserDoesNotExist
from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Passwords, ResetPassword
from eduiddashboard.vccs import add_credentials
from eduiddashboard.views import BaseFormView


def send_reset_password_mail(request, email):
    mailer = get_mailer(request)
    user = request.userdb.get_user(email)
    if not user:
        raise UserDoesNotExist()
    hash_code = md5(str(uuid.uuid4())).hexdigest()
    request.db.reset_passwords.insert({
        'email': email,
        'hash_code': hash_code,
        'verified': False,
    })
    verification_link = request.route_url("reset-password-form", code=hash_code)

    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "email": email,
        "given_name": user['givenName'],
        "verification_link": verification_link,
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

    def save_success(self, user_modified):
        passwords_data = self.schema.serialize(user_modified)
        new_password = passwords_data['new_password']
        old_password = passwords_data['old_password']

        # adding new credentials
        user = self.request.session['user']
        vccs_url = self.request.registry.settings.get('vccs_url')
        added = add_credentials(vccs_url, old_password, new_password, user)

        if added:
            self.request.session.flash(_('Your changes was saved, please, wait '
                                         'before your changes are distributed '
                                         'through all applications'),
                                       queue='forms')
        else:
            self.request.session.flash(_('Credentials has not been added for some reason.'
                                         ' Please contact with the system administrator.'),
                                       queue='forms')

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))


class BaseResetPasswordView(FormView):
    buttons = ('reset', )
    intro_message = None  # to override in subclasses

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


@view_config(route_name='reset-password', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordView(BaseResetPasswordView):
    """
    Reset user password.
    """
    schema = ResetPassword()
    route = 'reset-password'
    intro_message = _('Forgot your password?')

    def reset_success(self, passwordform):
        passwords_data = self.schema.serialize(passwordform)
        email = passwords_data['email']
        send_reset_password_mail(self.request, email)
        self.request.session.flash(_('An email has been sent to you with '
                                     'the instructions to reset your password.'))
        # TODO: finish implementation


@view_config(route_name='reset-password-form', permission='edit',
             renderer='templates/reset-password-form.jinja2')
class ResetPasswordFormView(BaseResetPasswordView):
    """
    Form to finish user password reset.
    """

    schema = Passwords()
    route = 'reset-password-form'
    buttons = ('reset', )
    intro_message = _('Finish your password reset')

    def reset_success(self, passwordform):
        self.request.session.flash(_('Password has been reset successfully'))
        # TODO: finish implementation
