## Passwords form

from pyramid.view import view_config
from bson import ObjectId

import vccs_client

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Passwords

from eduiddashboard.views import BaseFormView


@view_config(route_name='passwords', permission='edit',
             renderer='templates/passwords-form.jinja2')
class PasswordsView(BaseFormView):
    """
    Change user passwords
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = Passwords()
    route = 'passwords'

    def submit_success(self, user_modified):

        passwords = self.schema.serialize(user_modified)
        new_password = passwords['new_password']
        email = self.user['email']
        password_id = ObjectId()
        vccs = vccs_client.VCCSClient(
            base_url=self.request.registry.settings.get('vccs_url'),
        )
        new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                    credential_id=str(password_id))
        vccs.add_credentials(email, [new_factor])

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
