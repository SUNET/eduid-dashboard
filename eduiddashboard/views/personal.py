## Personal data form

from pyramid.view import view_config
from bson import ObjectId

import vccs_client

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person, Passwords

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


@view_defaults(route_name='passwords', permission='edit',
               renderer='templates/passwords-form.jinja2')
class Passwords(BaseFormView):
    """
    Change user passwords
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Passwords

    @view_config(request_method='GET')
    def get(self):
        return self.context

    @view_config(request_method='POST')
    def post(self):
        controls = self.request.POST.items()
        try:
            passwords = self.form.validate(controls)
        except ValidationFailure:
            return self.context

        passwords = self.schema.serialize(passwords)
        new_password = passwords['new_password']
        old_password = passwords['old_password']
        email = self.user['email']

        password_id = ObjectId()

        vccs = vccs_client.VCCSClient(
            base_url=self.request.registry.settings.get('vccs_url'),
        )
        old_factor = vccs_client.VCCSPasswordFactor(old_password,
                                                    credential_id=str(password_id))
        if not vccs.authenticate(email, [old_factor]):
            # TODO: include validation errors into form
            self.request.session.flash(_('ERROR: Your old password do not match'),
                                       queue='forms')
            return self.context

        new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                    credential_id=str(password_id))
        vccs.add_credentials(email, [new_factor])

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
        return self.context
