## Emails form

from deform import widget

from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.view import view_config


from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import EmailsPerson
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

    schema = EmailsPerson()
    route = 'emails'

    def before(self, form):
        form.bootstrap_form_style = ''
        form['email'].widget = widget.TextInputWidget(readonly=True)
        form['email'].title = _('Primary e-mail')

        form['emails']['emails']['verified'].widget = BooleanActionWidget(
            action=self.request.route_path('email-verification'),
            action_title=_('Resend the verification email')
        )

    def save_success(self, emailsform):
        emails = self.schema.serialize(emailsform)
        import ipdb; ipdb.set_trace()
        # update the session data

        # self.request.session['user'].update(emails)

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


def is_email_in_emails(email, emails):
    """
    emails is a dictionary like emails from person schema
    """
    for edict in emails:
        if email == edict['email']:
            return True
    return False


@view_config(route_name='email-verification', permission='edit',
             request_method='POST', renderer='json')
def email_verification(context, request):

    email = request.POST.get('email')

    if email is None:
        raise HTTPBadRequest(_('You forgive the email to verificate'))

    # TODO allow to take emails from context
    emails = EmailsPerson().serialize(request.session.get('user'))

    if not is_email_in_emails(email, emails['emails']):
        return HTTPNotFound(
            _('The given email is not in the user emails list')
        )

    # Do the email verification staff

    return {'success': True}
