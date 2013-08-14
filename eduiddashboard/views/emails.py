

## Emails form

from deform import ValidationFailure, widget

from pyramid.view import view_config, view_defaults

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import EmailsPerson

from eduiddashboard.views import BaseFormView


@view_defaults(route_name='emails', permission='edit',
               renderer='templates/emails-form.jinja2')
class EmailsView(BaseFormView):
    """
    Provide the handler to emails
        * GET = Rendering template
        * POST = Creating or modifing emails,
                    return status and flash message
    """

    schema = EmailsPerson
    route = 'emails'

    def __init__(self, context, request):
        super(EmailsView, self).__init__(context, request)
        self.form['emails'].widget = widget.SequenceWidget(min_len=1)

    @view_config(request_method='GET')
    def get(self):
        return self.context

    @view_config(request_method='POST')
    def post(self):

        controls = self.request.POST.items()
        try:
            emails = self.form.validate(controls)
        except ValidationFailure:
            return self.context

        emails = self.schema.serialize(emails)
        # update the session data
        self.request.session['user']['emails'].update(emails)

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

        self.context['object'] = emails
        return self.context
