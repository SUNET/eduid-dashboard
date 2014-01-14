## Emails form

import deform

from pyramid.view import view_config

from eduiddashboard.emails import send_verification_mail
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Email
from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(request, user):
    """
    Check if all emails are verified already

    return msg and icon
    """

    pending_actions, verification_needed = None, -1
    for n, email in enumerate(user.get('mailAliases', [])):
        if not email['verified']:
            pending_actions = _('An email address is pending confirmation')
            verification_needed = n
            break

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'completed': (0, 1),
            'verification_needed': verification_needed,
        }
    return {
        'completed': (1, 1),
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Email addresses'),
        'id': 'emails',
    }


def mark_as_verified_email(request, user, verified_email):
    emails = user['mailAliases']

    new_emails = []
    for email in emails:
        if email['email'] == verified_email:
            email['verified'] = True
        new_emails.append(email)

    user.update(new_emails)
    request.session.flash(_('Email {email} verified').format(email=verified_email),
                          queue='forms')


@view_config(route_name='emails-actions', permission='edit')
class EmailsActionsView(BaseActionsView):

    data_attribute = 'mailAliases'
    verify_messages = {
        'ok': _('Email address has been confirmed'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('Check your email for further instructions'),
        'placeholder': _('Email confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your email'),
    }

    def setprimary_action(self, index, post_data):
        mail = self.user['mailAliases'][index]
        if not mail.get('verified', False):
            return {
                'result': 'bad',
                'message': _("You need to confirm your email address before it can become primary"),
            }

        self.user['mail'] = mail['email']

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)
        return {'result': 'ok', 'message': _('Your primary email address was '
                                             'successfully changed')}

    def remove_action(self, index, post_data):
        emails = self.user['mailAliases']
        if len(emails) == 1:
            return {
                'result': 'error',
                'message': _('Error: You only have one email address and it  '
                             'can not be removed'),
            }
        remove_email = emails[index]['email']
        emails.remove(emails[index])

        self.user['mailAliases'] = emails
        primary_email = self.user.get('mail', '')

        if not primary_email or primary_email == remove_email:
            self.user['mail'] = emails[0]['email']

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('Email address was successfully removed'),
        }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify['email']

    def send_verification_code(self, data_id, code):
        send_verification_mail(self.request, data_id, code)


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

    buttons = (deform.Button(name='add', title=_('Add email address')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(EmailsView, self).get_template_context()
        context.update({
            'mails': self.user['mailAliases'],
            'primary_email': self.user['mail'],
        })

        return context

    def add_success(self, emailform):
        newemail = self.schema.serialize(emailform)

        # We need to add the new email to the emails list

        emails = self.user['mailAliases']

        mailsubdoc = {
            'email': newemail['mail'],
            'verified': False,
        }

        emails.append(mailsubdoc)

        self.user.update(emails)

        # Do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')

        send_verification_mail(self.request, newemail['mail'])

        self.request.session.flash(_('A confirmation email has been sent to your email address. '
                                     'Please enter your confirmation code <a href="#" class="verifycode" data-identifier="${id}">here</a>.',
                                     mapping={'id': len(emails)}),
                                   queue='forms')
