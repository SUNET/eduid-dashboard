## Postal address forms

import logging

from deform import widget
import pycountry

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import PostalAddress
from eduiddashboard.views import BaseFormView, BaseActionsView

logger = logging.getLogger(__name__)


def contains_official_postal_address(postal_address):
    for address in postal_address:
        if address['type'] == 'official':
            return True
    return False


def get_status(user):
    """
    Check if all postal addresses are verified already

    return msg and icon
    """
    postal_address = user.get('postalAddress', [])

    if not contains_official_postal_address(postal_address):
        return {
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


def get_address_id(address):
    return u'%s, %s %s, %s' % (address['address'],
                               address['postalCode'],
                               address['locality'],
                               address['country'])


def mark_as_verified_postal_address(request, user, address_id):
    addresses = user['postalAddress']

    for address in addresses:
        if get_address_id(address) == address_id:
            address['verified'] = True


@view_config(route_name='postaladdress-actions', permission='edit')
class PostalAddressActionsView(BaseActionsView):
    data_attribute = 'postalAddress'
    verify_messages = {
        'ok': _('The postal address has been verified'),
        'error': _('The confirmation code used is invalid, please try again or request a new code'),
        'request': _('Please revise your postal mailbox and fill below with the given code'),
        'placeholder': _('Postal address confirmation code'),
        'new_code_sent': _('A new confirmation code has been sent to your postal mailbox'),
    }

    def get_verification_data_id(self, data_to_verify):
        return get_address_id(data_to_verify)

    def send_verification_code(self, data_id, code):
        msg = _('The confirmation code for your postal address is ${code}', mapping={
            'code': code,
        })
        msg = get_localizer(self.request).translate(msg)
        logger.info(u"Postal mail to %s: %s" % (data_id, msg))

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
        return {'result': 'ok', 'message': _('Your postal address was successfully updated')}

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
            'message': _('Postal address was successfully removed.'),
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
        postal_address = self.user.get('postalAddress', [])
        context.update({
            'postal_addresses': postal_address,
            'contains_official_postal_address': contains_official_postal_address(postal_address),
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

        self.request.session.flash(_('Changes saved.'), queue='forms')
