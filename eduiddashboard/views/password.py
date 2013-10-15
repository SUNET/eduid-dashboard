## Passwords form

from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render
from pyramid.view import view_config

from pyramid_deform import FormView
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduid_am.exceptions import UserDoesNotExist
from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Passwords, ResetPassword, ResetPasswordStep2
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


def send_reset_password_mail(request, email):
    """ Send an email with the instructions for resetting password """
    mailer = get_mailer(request)
    user = request.userdb.get_user(email)
    if not user:
        raise UserDoesNotExist()
    hash_code = get_unique_hash()

    request.db.reset_passwords.insert({
        'email': email,
        'hash_code': hash_code,
        'verified': False,
    }, safe=True)

    reset_password_link = request.route_url("reset-password-step2", code=hash_code)

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
    buttons = ('reset', )
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
        flash(self.request, 'info', _('An email has been sent to the address you entered.'
                                      'This email will contain instructions and a link'
                                      'that will let you reset your password.'))
        return {
            'message': _('Please read the email sent to you for further instructions. This window can now safely be closed.'),
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
        user = self.request.userdb.get_user(reset_password['email'])

        new_password = passwordform['new_password']
        ok = change_password(self.request, user, '', new_password)
        if ok:
            self.request.db.reset_passwords.remove({'_id': reset_password['_id']})
            flash(self.request, 'info', _('Password has been reset successfully'))
        else:
            flash(self.request, 'info', _('An error has occured while updating your password,'
                                          'please try again or contact support if the problem persists.'))
        return {
            'message': _('You can now log in by <a href="${homelink}">clicking here</a>',
                         mapping={'homelink': self.request.route_url('profile-editor')}),
        }
