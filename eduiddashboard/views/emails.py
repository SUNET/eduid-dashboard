## Emails form

from pyramid.view import view_config

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Email

from eduiddashboard.views import BaseFormView
from eduiddashboard.emails import send_verification_mail


def mark_as_verified_email(request, verified_email):
        user = request.session.get('user')
        emails = user['emails']

        new_emails = []
        for email in emails:
            if email['email'] == verified_email:
                email['verified'] = True
            new_emails.append(email)

        request.session['user'].update(new_emails)
        user.update(new_emails)

        # Do the save staff
        request.db.profiles.find_and_modify({
            '_id': user['_id'],
        }, user, upsert=True, safe=True)

        update_attributes.delay('eduid_dashboard', str(user['_id']))

        request.session.flash(_('Your email {email} was verified'
                                ).format(email=verified_email),
                              queue='forms')


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

    buttons = ('add', 'verify', 'remove', 'setprimary')

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(EmailsView, self).get_template_context()

        context.update({
            'emails': self.user['emails'],
            'primary_email': self.user['email'],
        })

        return context

    def add_success(self, emailform):
        newemail = self.schema.serialize(emailform)

        # We need to add the new email to the emails list

        emails = self.user['emails']

        emails.append({
            'email': newemail['email'],
            'verified': False,
        })

        self.request.session['user'].update(emails)
        self.user.update(emails)

        # Do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, self.user, upsert=True, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

        send_verification_mail(self.request, newemail['email'])

        self.request.session.flash(_('A verification email has been sent '
                                     'to your new account. Please revise your '
                                     'inbox and click on the provided link'),
                                   queue='forms')

    def remove_success(self, emailform):
        remove_email = self.schema.serialize(emailform)

        emails = self.user['emails']

        new_emails = []
        for email in emails:
            if email['email'] != remove_email['email']:
                new_emails.append(email)

        self.request.session['user']['emails'] = new_emails
        if not self.user.get('email', ''):
            self.request.session['user']['email'] = new_emails[0]['email']

        self.user = self.request.session['user']
        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, self.user, upsert=True, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('One email has been removed, please, wait'
                                     ' before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

    def verify_success(self, emailform):
        email = self.schema.serialize(emailform)

        send_verification_mail(self.request, email['email'])

        self.request.session.flash(_('A new verification email has been sent '
                                     'to your account. Please revise your '
                                     'inbox and click on the provided link'),
                                   queue='forms')

    def setprimary_success(self, emailform):
        email = self.schema.serialize(emailform)
        primary_email = email.get('email')

        self.request.session['user']['email'] = primary_email

        # do the email verification staff

        self.request.session.flash(_('Your primary email was changed'),
                                   queue='forms')
