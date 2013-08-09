
## Personal data form

import json

from deform import Form, ValidationFailure

from pyramid.view import view_config, view_defaults

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person


@view_defaults(route_name='personaldata', permission='edit',
               renderer='templates/personaldata-form.jinja2')
class PersonalData(object):
    """
    Provide the handler to personal data form
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    def __init__(self, request):
        self.request = request
        self.user = request.session.get('user', None)
        self.schema = Person()
        url = self.request.route_url('personaldata')

        ajax_options = {
            'replaceTarget': True,
            'url': url,
            'target': "div.profile-form"
        }

        self.form = Form(self.schema, buttons=('submit',),
                         use_ajax=True,
                         ajax_options=json.dumps(ajax_options))

        self.context = {
            'form': self.form,
            'person': self.schema.serialize(self.user),
        }

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

        self.person = self.schema.serialize(user_modified)
        # update the session data
        self.request.session['user'].update(self.person)

        # Do the save staff

        # TODO Avoid delete items from queue
        # Remove items from changes queue, if exists
        self.request.db.profiles.remove({
            '_id': self.user['_id'],
        })

        # Insert the new user object
        self.request.db.profiles.insert(self.user, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

        self.context['person'] = self.person
        return self.context
