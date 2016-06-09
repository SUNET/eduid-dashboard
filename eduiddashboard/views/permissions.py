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
    attribute = 'eduPersonEntitlement'

    def get_template_context(self):
        tempcontext = super(PermissionsView, self).get_template_context()
        session_user = get_session_user(self.request, raise_on_not_logged_in = False)
        if self.context.user.eppn == session_user.eppn:
            tempcontext['confirmation_required'] = True
        else:
            tempcontext['confirmation_required'] = False
        return tempcontext

    def save_success(self, permform):
        data = self.schema.serialize(permform)
        self.user.entitlements.extend(data[self.attribute])
        try:
            self.context.save_dashboard_user(self.user)
        except UserOutOfSync:
            self.sync_user()
        else:
            message = _('Changes saved.')
            self.request.session.flash(
                    get_localizer(self.request).translate(message),
                    queue='forms')
