## Postal address forms

from deform import widget
import pycountry
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import PostalAddress
from eduiddashboard.utils import get_icon_string
from eduiddashboard.views import BaseFormView, BaseActionsView


def get_status(user):
    """
    Check if all postal addresses are verified already

    return msg and icon
    """

    pending_actions = None
    postalAddress = user.get('postalAddress', [])
    if not postalAddress:
        pending_actions = _('You have to add a postal address')
    else:
        for address in postalAddress:
            if not address['verified']:
                pending_actions = _('You have to verificate some postal address')

    if pending_actions:
        return {
            'icon': get_icon_string('warning-sign'),
            'pending_actions': pending_actions,
            'completed': (0, 1),
        }
    return {
        'completed': (1, 1),
    }


def get_tab():
    return {
        'status': get_status,
        'label': _('Postal Address'),
        'id': 'postaladdress',
    }


@view_config(route_name='postaladdress-actions', permission='edit')
class PostalAddressActionsView(BaseActionsView):

    def setpreferred_action(self, index, post_data):
        addresses = self.user.get('postalAddress', [])
        preferred_address = addresses[index]
        for address in addresses:
            if address == preferred_address:
                address['preferred'] = True
            else:
                address['preferred'] = False

        self.user['postalAddress'] = addresses
        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'postalAddress': addresses,
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)
        return {'result': 'ok', 'message': _('Your preferred address was changed')}

    def remove_action(self, index, post_data):
        addresses = self.user['postalAddress']
        address_to_remove = addresses[index]
        addresses.remove(address_to_remove)

        self.user['postalAddress'] = addresses

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'postalAddress': addresses,
            }
        }, safe=True)

        self.context.propagate_user_changes(self.user)

        return {
            'result': 'ok',
            'message': _('One address has been removed, please, wait'
                         ' before your changes are distributed '
                         'through all applications'),
        }


@view_config(route_name='postaladdress', permission='edit',
             renderer='templates/postaladdress-form.jinja2')
class PostalAddressView(BaseFormView):
    """
    Change user postal address
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = PostalAddress()
    route = 'postaladdress'

    buttons = ('add', )

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(PostalAddressView, self).get_template_context()
        context.update({
            'postal_addresses': self.user.get('postalAddress', []),
        })
        return context

    def before(self, form):
        allowed_countries_in_settings = self.request.registry.settings.get('allowed_countries')
        if allowed_countries_in_settings:
            allowed_countries = [l.split('=') for l in allowed_countries_in_settings.splitlines() if l]
        else:
            allowed_countries = [(c.alpha2, c.name) for c in pycountry.countries]

        form['country'].widget = widget.SelectWidget(values=[(code.strip(), country.strip()) for code, country in allowed_countries])

    def add_success(self, addressform):
        address = self.schema.serialize(addressform)
        address['verified'] = False

        addresses = self.user.get('postalAddress', [])
        if len(addresses) == 0:
            address['preferred'] = True
        else:
            address['preferred'] = False
        addresses.append(address)

        # update the session data
        self.user['postalAddress'] = addresses

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$set': {
                'postalAddress': addresses,
            }
        }, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
