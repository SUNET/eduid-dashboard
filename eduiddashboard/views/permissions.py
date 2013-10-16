## Permissions form (eduPersonEntitlement)

from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Permissions

from eduiddashboard.views import BaseFormView, get_dummy_status


def get_tab():
    return {
        'status': get_dummy_status,
        'label': _('Permissions'),
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
        if self.context.user[ma] == self.request.session.get('user', {}).get(ma):
            tempcontext['confirmation_required'] = True
        else:
            tempcontext['confirmation_required'] = False
        return tempcontext

    def save_success(self, new_entitletments):

        # Insert the new user object
        self.user.update(new_entitletments)

        self.request.db.profiles.save(self.user, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Changes saved.'), queue='forms')
