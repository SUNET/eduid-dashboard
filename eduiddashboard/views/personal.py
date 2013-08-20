## Personal data form

from pyramid.view import view_config

from eduid_am.tasks import update_attributes

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

    def submit_success(self, user_modified):

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
