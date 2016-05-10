## Emails form

import deform
from datetime import datetime

from pyramid.view import view_config
from pyramid.i18n import get_localizer

from eduid_userdb.exceptions import UserOutOfSync
from eduid_userdb.element import PrimaryElementViolation
from eduid_userdb.mail import MailAddress
from eduiddashboard.emails import send_verification_mail
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Email
from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView, BaseActionsView
from eduiddashboard.session import get_session_user


def get_status(request, user):
    """
    Check if all emails are verified already

    return msg and icon
    """

    pending_actions = None
    pending_action_type = ''
    verification_needed = -1
    completed = 0
    for n, email in enumerate(user.mail_addresses.to_list()):
        if email.is_verified:
            completed = 1
        elif pending_actions is None:
            pending_actions = _('An email address is pending confirmation')
            pending_actions = get_localizer(request).translate(pending_actions)
            pending_action_type = 'verify'
            verification_needed = n

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'pending_action_type': pending_action_type,
            'completed': (completed, 1),
            'verification_needed': verification_needed,
        }
    return {
        'completed': (completed, 1),
    }


def get_tab(request):
    label = _('Email addresses')
    label = get_localizer(request).translate(label)
    return {
        'status': get_status,
        'label': label,
        'id': 'emails',
    }


@view_config(route_name='emails-actions', permission='edit')
class EmailsActionsView(BaseActionsView):

    data_attribute = 'mailAliases'
    special_verify_messages = {
        'success': _('Email address has been confirmed'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('Check your email inbox for {data} for further instructions'),
        'placeholder': _('Email confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your email'),
    }

    def setprimary_action(self, index, post_data):

        try:
            mail = self.user.mail_addresses.to_list()[index]
        except IndexError:
            return self.sync_user()

        if not mail.is_verified:
            message = _('You need to confirm your email address '
                        'before it can become primary')
            return {
                'result': 'bad',
                'message': get_localizer(self.request).translate(message),
            }

        self.user.mail_addresses.primary = mail.email
        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            return self.sync_user()

        self.request.stats.count('dashboard/email_set_primary', 1)
        message = _('Your primary email address was '
                    'successfully changed')
        return {'result': 'success',
                'message': get_localizer(self.request).translate(message)}

    def remove_action(self, index, post_data):
        emails = self.user.mail_addresses.to_list()
        if len(emails) == 1:
            message = _('Error: You only have one email address and it  '
                        'can not be removed')
            return {
                'result': 'error',
                'message': get_localizer(self.request).translate(message),
            }

        try:
            remove_email = emails[index].email
        except IndexError:
            return self.sync_user()

        try:
            self.user.mail_addresses.remove(remove_email)
        except PrimaryElementViolation:
            new_index = 0 if index != 0 else 1
            self.user.mail_addresses.primary = emails[new_index].email
            self.user.mail_addresses.remove(remove_email)

        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            return self.sync_user()

        self.request.stats.count('dashboard/email_removed', 1)
        message = _('Email address was successfully removed')
        return {
            'result': 'success',
            'message': get_localizer(self.request).translate(message),
        }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify['email']

    def send_verification_code(self, data_id, reference, code):
        send_verification_mail(self.request, data_id, reference, code)


@view_config(route_name='emails', permission='edit',
             renderer='templates/emails-form.jinja2')
class EmailsView(BaseFormView):
    """
    Provide the handler to emails
        * GET = Rendering template
        * POST = Creating or modifing emails,
                    return status and flash message
    """
    schema = Email()
    route = 'emails'

    buttons = (deform.Button(name='add', title=_('Add')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(EmailsView, self).get_template_context()
        context.update({
            'mails': self.user.mail_addresses.to_list(),
            'primary_email': self.user.mail_addresses.primary.email,
        })

        return context

    def add_success(self, emailform):
        newemail = self.schema.serialize(emailform)

        new_email = MailAddress(email=newemail['mail'],
                application='dashboard',
                verified=False, primary=False)

        self.user = get_session_user(self.request)
        self.user.mail_addresses.add(new_email)
        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            self.sync_user()

        else:
            message = _('Changes saved')
            self.request.session.flash(get_localizer(self.request).translate(message), queue='forms')

            send_verification_mail(self.request, newemail['mail'])

            second_msg = _('A confirmation email has been sent to your email '
                    'address. Please enter your confirmation code '
                    '<a href="#" class="verifycode" '
                    'data-identifier="${id}">here</a>.', mapping={'id': self.user.mail_addresses.count})
            self.request.session.flash(get_localizer(self.request).translate(second_msg), queue='forms')
