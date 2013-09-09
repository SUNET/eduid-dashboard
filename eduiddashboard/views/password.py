## Passwords form

from pyramid.view import view_config
from bson import ObjectId

import vccs_client

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Passwords
from eduiddashboard.vccs import add_credentials
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

    def save_success(self, user_modified):
        passwords_data = self.schema.serialize(user_modified)
        new_password = passwords_data['new_password']
        old_password = passwords_data['old_password']

        # adding new credentials
        user = self.request.session['user']
        vccs_url = self.request.registry.settings.get('vccs_url')
        added = add_credentials(vccs_url, old_password, new_password, user)

        if added:
            self.request.session.flash(_('Your changes was saved, please, wait '
                                         'before your changes are distributed '
                                         'through all applications'),
                                       queue='forms')
        else:
            self.request.session.flash(_('Credentials has not been added for some reason.'
                                         ' Please contact with the system administrator.'),
                                       queue='forms')

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))