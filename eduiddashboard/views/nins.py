# NINS form

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPConflict

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN
from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView, BaseActionsView

from eduiddashboard.verifications import dummy_message, get_verification_code


def send_verification_message(request, nin):
    """
    You need to replace the call to dummy_message with the govt
    message api
    """

    code = get_verification_code(request.db, 'nins', nin)
    verification_message = _(
        'This is a message from %(site)s. The code for validate '
        'your NIN %(nin)s is %(code)s ' % {
            'nin': nin,
            'code': code,
            'site': request.registry.settings.get('site.name',
                                                  'eduID dashboard'),
        }
    )

    ## Replace this call
    dummy_message(request, verification_message)


def get_status(user):
    """
    Check if there is one norEduPersonNIN active and verified
        is already verified if the active NIN was verified

    return msg and icon
    """
    schema = NIN()

    completed_fields = 0
    pending_actions = None

    for field in schema.children:
        if user.get(field.name, None) is not None:
            completed_fields += 1

    nins = user.get('norEduPersonNIN', [])
    if len(nins) > 0:
        active_nin = nins[-1]
        if not active_nin.get('verified', False):
            pending_actions = _('You must validate your NIN number')
        elif not active_nin.get('active', False):
            pending_actions = _('You have to add your NIN number')
        else:
            completed_fields += 1

    status = {
        'completed': (completed_fields, len(schema.children) + 1)
    }
    if pending_actions:
        status.update({
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,

        })
    return status


def get_tab():
    return {
        'status': get_status,
        'label': _('National identity number'),
        'id': 'nins',
    }


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    def verify_action(self, index, post_data):
        """ Only the active (the last one) NIN can be verified """
        nin = self.user['norEduPersonNIN'][-1]

        already_verified = self.request.userdb.exists_by_field(
            'norEduPersonNIN', {
                'norEduPersonNIN': nin['norEduPersonNIN'],
                'verified': True,
            }
        )
        if already_verified:
            return {
                'result': 'bad',
                'message': _("This norEduPersonNIN has been verified by "
                             "someone else in his profile, so then, you "
                             "can't verify it as yours. Please, contact "
                             "with technical support")
            }

        send_verification_message(self.request, nin['norEduPersonNIN'])

        return {
            'result': 'ok',
            'message': _('A verification message has been sent '
                         'to your Govt Inbox. Please revise your '
                         'inbox and return to this page to enter '
                         'the provided verification number'),
        }

    def remove_action(self, index, post_data):
        """ Only not verified nins can be removed """
        nins = self.user.get('norEduPersonNIN', [])
        remove_nin = nins[index]

        if remove_nin['verified']:
            raise HTTPConflict("This nin can't be removed")

        nins.remove(nins[index])

        self.user['norEduPersonNIN'] = nins

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$pull': {
                'norEduPersonNIN': {
                    'norEduPersonNIN': remove_nin['norEduPersonNIN'],
                }
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('The nin has been removed, please, wait'
                         ' before your changes are distributed '
                         'through all applications'),
        }


@view_config(route_name='nins', permission='edit',
             renderer='templates/nins-form.jinja2')
class NinsView(BaseFormView):
    """
    Provide the handler to emails
        * GET = Rendering template
        * POST = Creating or modifing nins,
                    return status and flash message
    """
    schema = NIN()
    route = 'nins'

    buttons = ('add', )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(NinsView, self).get_template_context()
        context.update({
            'nins': self.user['norEduPersonNIN'],
        })

        return context

    def add_success(self, ninform):
        newnin = self.schema.serialize(ninform)

        # only one nin verified can be actived
        ninsubdoc = {
            'norEduPersonNIN': newnin['norEduPersonNIN'],
            'verified': False,
            'active': False,
        }

        nins = self.user['norEduPersonNIN']
        nins.append(ninsubdoc)

        self.user['norEduPersonNIN'] = nins

        # Do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$push': {
                'norEduPersonNIN': ninsubdoc
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')

        send_verification_message(self.request, newnin['norEduPersonNIN'])

        self.request.session.flash(_('A verification message has been sent '
                                     'to your Govt Inbox. Please revise your '
                                     'inbox and return to this page to enter '
                                     'the provided verification number'),
                                   queue='forms')
