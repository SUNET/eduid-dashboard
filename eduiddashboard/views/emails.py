## Emails form

from pyramid.view import view_config

from eduiddashboard.emails import send_verification_mail
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Email
from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(user):
    """
    Check if all emails are verified already

    return msg and icon
    """

    pending_actions = None
    for email in user.get('mailAliases', []):
        if not email['verified']:
            pending_actions = _('You have to verificate some emails')
            break

    if pending_actions:
        msg = _('You have to verificate some emails')
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': msg,
            'completed': (0, 1),
        }
    return {
        'completed': (1, 1),
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Emails'),
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
    request.session.flash(_('The email {email} was verified'
                          ).format(email=verified_email),
                          queue='forms')


@view_config(route_name='emails-actions', permission='edit')
class EmailsActionsView(BaseActionsView):

    def setprimary_action(self, index, post_data):
        primary_email = self.user['mailAliases'][index]['email']
        self.user['mail'] = primary_email

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'mail': primary_email,
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)
        return {'result': 'ok', 'message': _('Your primary email was changed')}

    def verify_action(self, index, post_data):
        email = self.user['mailAliases'][index]

        send_verification_mail(self.request, email['email'])

        return {
            'result': 'ok',
            'message': _('A new verification email has been sent '
                         'to your account. Please revise your '
                         'inbox and click on the provided link'),
        }

    def remove_action(self, index, post_data):
        emails = self.user['mailAliases']
        if len(emails) == 1:
            return {
                'result': 'error',
                'message': _('Error: You only have one email and this cannot be deleted'),
            }
        remove_email = emails[index]['email']
        emails.remove(emails[index])

        self.user['mailAliases'] = emails
        primary_email = self.user.get('mail', '')

        if not primary_email or primary_email == remove_email:
            self.user['mail'] = emails[0]['email']

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$pull': {
                'mailAliases': {
                    'email': remove_email,
                }
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('One email has been removed, please, wait'
                         ' before your changes are distributed '
                         'through all applications'),
        }


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

    buttons = ('add', )

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
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$push': {
                'mailAliases': mailsubdoc
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

        send_verification_mail(self.request, newemail['mail'])

        self.request.session.flash(_('A verification email has been sent '
                                     'to your new account. Please revise your '
                                     'inbox and click on the provided link'),
                                   queue='forms')
