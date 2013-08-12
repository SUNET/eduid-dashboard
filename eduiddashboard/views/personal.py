
## Personal data form

from deform import ValidationFailure

from pyramid.view import view_config, view_defaults

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person

from eduiddashboard.views import BaseFormView


@view_defaults(route_name='personaldata', permission='edit',
               renderer='templates/personaldata-form.jinja2')
class PersonalData(BaseFormView):
    """
    Provide the handler to personal data form
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Person

    @view_config(request_method='GET')
    def get(self):
        return self.context

    @view_config(request_method='POST')
    def post(self):

        controls = self.request.POST.items()
        try:
            user_modified = self.form.validate(controls)
        except ValidationFailure:
            return self.context

        person = self.schema.serialize(user_modified)
        # update the session data
        self.request.session['user'].update(person)

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

        self.context['object'] = person
        return self.context
