## Personal data form

from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person

from eduiddashboard.views import BaseFormView


@view_config(route_name='personaldata', permission='edit',
             renderer='templates/personaldata-form.jinja2')
class PersonalDataView(BaseFormView):
    """
    Provide the handler to personal data form
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Person()
    route = 'personaldata'

    def save_success(self, user_modified):
        person = self.schema.serialize(user_modified)

        # Insert the new user object
        self.user.update(person)
        self.request.db.profiles.save(self.user, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
