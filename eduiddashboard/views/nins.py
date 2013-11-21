# NINS form

import deform

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPConflict, HTTPNotFound
from pyramid.i18n import get_localizer

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import NIN
from eduiddashboard.utils import get_icon_string, get_short_hash
from eduiddashboard.views import BaseFormView, BaseActionsView
from eduiddashboard import log

from eduiddashboard.verifications import new_verification_code


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
        if not active_nin.get('active', False):
            pending_actions = _('Add national identity number')
        elif not active_nin.get('verified', False):
            pending_actions = _('Validation required for national identity number')
        else:
            completed_fields += 1
    else:
        pending_actions = _('Add national identity number')

    status = {
        'completed': (completed_fields, len(schema.children) + 1)
    }
    if pending_actions:
        status.update({
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
        })
    return status


def send_verification_code(request, user, nin, code=None):
    """
    You need to replace the call to dummy_message with the govt
    message api
    """

    if code is None:
        code = new_verification_code(request, 'norEduPersonNIN', nin, user,
                                     hasher=get_short_hash)

    language = request.context.get_preferred_language()

    request.msgrelay.nin_validator(nin, code, language)


def mark_as_verified_nin(request, user, verified_nin):
    nins = user['norEduPersonNIN']

    for nin in nins:
        if nin['norEduPersonNIN'] == verified_nin:
            nin['verified'] = True
            nin['active'] = True
        else:
            nin['active'] = False


def post_verified_nin(request, user, verified_nin):
    """
        Function to get the official postal address from
        the government service
    """
    log.debug('Retrieving postal address from NIN service')
    log.warning('The postal addresss service communication is not implemented')


def get_tab():
    return {
        'status': get_status,
        'label': _('National identity number'),
        'id': 'nins',
    }


@view_config(route_name='nins-actions', permission='edit')
class NINsActionsView(BaseActionsView):

    data_attribute = 'norEduPersonNIN'
    verify_messages = {
        'ok': _('National identity number verified'),
        'error': _('The confirmation code is invalid, please try again or request a new code'),
        'request': _('A confirmation code has been sent to your govt mailbox'),
        'placeholder': _('National identity number confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your govt mailbox'),
    }

    def get_verification_data_id(self, data_to_verify):
        return data_to_verify[self.data_attribute]

    def verify_action(self, index, post_data):
        """ Only the active (the last one) NIN can be verified """
        nins = self.user.get(self.data_attribute, {})
        if index != len(nins) - 1:
            return {
                'result': 'bad',
                'message': _("The provided nin can't be verified. You only "
                             'can verify the last one'),
            }
        return super(NINsActionsView, self).verify_action(index, post_data)

    def remove_action(self, index, post_data):
        """ Only not verified nins can be removed """
        nins = self.user.get('norEduPersonNIN', [])
        if len(nins) > index:
            remove_nin = nins[index]
        else:
            raise HTTPNotFound("The index provides can't be found")

        remove_nin = nins[index]

        if remove_nin['verified']:
            raise HTTPConflict("This nin can't be removed")

        nins.remove(nins[index])

        self.user['norEduPersonNIN'] = nins

        # do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('National identity number has been removed'),
        }

    def send_verification_code(self, data_id, code):
        send_verification_code(self.request, self.user, data_id, code)


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

    buttons = (deform.Button(name='add', title=_('Add national identity number')), )

    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(NinsView, self).get_template_context()
        proofing_links = self.request.registry.settings.get('proofing_links',
                                                            {})
        proofing_link = proofing_links.get('nin')
        context.update({
            'nins': self.user.get('norEduPersonNIN', []),
            'proofing_link': proofing_link,
        })

        return context

    def add_success_personal(self, ninform):
        newnin = self.schema.serialize(ninform)
        newnin = newnin['norEduPersonNIN']

        ninsubdoc = {
            'norEduPersonNIN': newnin,
            'verified': False,
            'active': False,
        }

        nins = self.user.get('norEduPersonNIN', [])
        nin_identifier = len(nins)
        nins.append(ninsubdoc)

        self.user['norEduPersonNIN'] = nins

        # Do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')

        send_verification_code(self.request, self.user, newnin)

        msg = _('A confirmation code has been sent to your govt inbox. '
                'Please click on "Pending confirmation" link below to enter.'
                'your confirmation code',
                mapping={'id': nin_identifier})

        msg = get_localizer(self.request).translate(msg)
        self.request.session.flash(msg, queue='forms')

    def add_success_other(self, ninform):
        newnin = self.schema.serialize(ninform)
        newnin = newnin['norEduPersonNIN']

        nins = self.user.get('norEduPersonNIN', [])

        for nin in nins:
            nin['active'] = False

        ninsubdoc = {
            'norEduPersonNIN': newnin,
            'verified': True,
            'active': True,
        }

        nins.append(ninsubdoc)

        self.user['norEduPersonNIN'] = nins

        # Do the save staff
        self.request.db.profiles.save(self.user, safe=True)

        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Changes saved'),
                                   queue='forms')

    def add_success(self, ninform):
        if self.context.workmode == 'personal':
            self.add_success_personal(ninform)
        else:
            self.add_success_other(ninform)
