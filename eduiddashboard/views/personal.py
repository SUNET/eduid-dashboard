## Personal data form

from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person

from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView


def get_status(user):
    """
    Check if there is one norEduPersonNIN active and verified
        is already verified if the active NIN was verified

    return msg and icon
    """
    schema = Person()

    completed_fields = 0
    pending_actions = []
    for field in schema.children:
        if field.name == 'norEduPersonNIN':
            nins = user.get(field.name, [])
            nin_pending = True
            for nin in nins:
                if nin.get('verified') and nin.get('active'):
                    completed_fields += 1
                    nin_pending = False
            if not nins:
                pending_actions = _('You have to add your NIN number')
            elif nin_pending:
                pending_actions = _('You must validate your NIN number')

        else:
            if user.get(field.name, None) is not None:
                completed_fields += 1

    icon = get_icon_string('warning-sign')
    return {
        'icon': icon,
        'msg': '',
        'completed': (completed_fields, len(schema.children)),
        'pending_actions': pending_actions,
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Personal info'),
        'id': 'personaldata',
    }


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

    def before(self, form):
        workmode = self.context.workmode
        if workmode == 'personal':
            form['norEduPersonNIN'].widget.readonly = True

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
