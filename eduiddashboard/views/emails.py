## Emails form

from deform import widget

from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.view import view_config

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Email
from eduiddashboard.widgets import (BooleanActionWidget)

from eduiddashboard.views import BaseFormView


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

    buttons = ('save', 'verify', 'remove',)

    def appstruct(self):
        return {}

    def show(self, form):
        context = super(BaseFormView, self).show(form)

        from pprint import pprint
        pprint(self.user['emails'])
        pprint(self.request.session['user']['emails'])

        context.update({
            'formname': self.classname,
            'emails': self.user['emails'],
        })

        return context

    def save_success(self, emailform):
        newemail = self.schema.serialize(emailform)

        # We need to add the new email to the emails list

        emails = self.user['emails']

        emails.append({
            'email': newemail['email'],
            'verified': False,
        })

        self.request.session['user'].update(emails)

        # Do the save staff

        # Insert the new user object
        # self.request.db.profiles.update({
        #     '_id': self.user['_id'],
        # }, self.user, safe=True)

        # update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

    def remove_success(self, emailform):
        remove_email = self.schema.serialize(emailform)

        emails = self.user['emails']



        new_emails = {}
        for email in emails:
            if email['email'] != remove_email['email']:
                new_emails.append(email)

        self.request.session['user']['emails'] = emails
        self.request.session['email'] = new_emails[0]['email']

        # do the save staff

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

    def verify_success(self, emailform):
        email = self.schema.serialize(emailform)

        # do the email verification staff

        self.request.session.flash(_('A verification email has been sent to '
                                     'the new account. Please revise your '
                                     'inbox and click on the provided link'),
                                   queue='forms')
