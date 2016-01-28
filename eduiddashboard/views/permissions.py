## Permissions form (eduPersonEntitlement)

from pyramid.view import view_config
from pyramid.i18n import get_localizer

from eduid_userdb.dashboard import DashboardLegacyUser as OldUser
from eduid_userdb.dashboard import DashboardUser
from eduid_userdb.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Permissions
from eduiddashboard.session import get_session_user
from eduiddashboard.views import BaseFormView, get_dummy_status


def get_tab(request):
    label = _('Permissions')
    return {
        'status': get_dummy_status,
        'label': get_localizer(request).translate(label),
        'id': 'permissions',
    }


@view_config(route_name='permissions', permission='edit',
             renderer='templates/permissions-form.jinja2')
class PermissionsView(BaseFormView):
    """
    Provide the handler to permissions form
        * GET = Rendering template
        * POST = Creating or modifing permissions,
                    return status and flash message
    """

    schema = Permissions()
    route = 'permissions'
    attributte = 'eduPersonEntitlement'

    def get_template_context(self):
        tempcontext = super(PermissionsView, self).get_template_context()
        ma = self.context.main_attribute
        user = get_session_user(self.request, raise_on_not_logged_in = False, legacy_user = False)
        if self.context.user.to_dict().get(ma) == user.to_dict().get(ma):
            tempcontext['confirmation_required'] = True
        else:
            tempcontext['confirmation_required'] = False
        return tempcontext

    def save_success(self, new_entitlements):

        # Insert the new user object
        self.user.entitlements.append(new_entitlements)
        try:
            self.request.userdb_new.save(self.user)
        except UserOutOfSync:
            self.sync_user()
        else:
            message = _('Changes saved.')
            self.request.session.flash(
                    get_localizer(self.request).translate(message),
                    queue='forms')
