

## Emails form

from deform import widget

from pyramid.view import view_config


from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import EmailsPerson

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

    schema = EmailsPerson()
    route = 'emails'

    def before(self, form):
        form['emails'].widget = widget.SequenceWidget(min_len=1)
        form['emails'].title = ""

        form['email'].widget = widget.TextInputWidget(readonly=True)
        form['email'].title = _('Primary e-mail')

    def submit_success(self, emailsform):
        emails = self.schema.serialize(emailsform)
        # update the session data
        for email_dict in emails.get('emails', {}):
            if email_dict.get('primary', False):
                emails['email'] = email_dict.get('email')

        self.request.session['user'].update(emails)

        # Do the save staff

        # Insert the new user object
        self.request.db.profiles.update({
            '_id': self.user['_id'],
        }, self.user, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
