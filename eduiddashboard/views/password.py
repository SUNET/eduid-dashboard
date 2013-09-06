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
        # adding new credentials
        password_id = ObjectId()
        new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                    credential_id=str(password_id))
        if vccs.add_credentials(email, [new_factor]):
            self.request.session.flash(_('Your changes was saved, please, wait '
                                         'before your changes are distributed '
                                         'through all applications'),
                                       queue='forms')
        else:
            self.request.session.flash(_('Credentials has not been added for some reason.'
                                         ' Please contact with the system administrator.'),
                                       queue='forms')
        # revoking old credentials
        old_password_id = self.request.session['user']['passwords'][0]['id']
        old_factor = vccs_client.VCCSRevokeFactor(str(old_password_id), 'changing password', reference='dashboard')
        vccs.revoke_credentials(email, [old_factor])
