## Postal address forms

import logging

from deform import widget, Button
import pycountry

from pyramid.i18n import get_localizer
from pyramid.view import view_config

from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import PostalAddress
from eduiddashboard.views import BaseFormView

logger = logging.getLogger(__name__)


def contains_official_postal_address(postal_address):
    for address in postal_address:
        if address['type'] == 'official':
            return True
    return False


def get_status(request, user):
    """
    Check if all postal addresses are verified already

    return msg and icon
    """
    postal_address = user.get_addresses()

    if not contains_official_postal_address(postal_address):
        return {
            'completed': (0, 1),
        }
    return {
        'completed': (1, 1),
    }


def get_tab(request):
    label = _('Postal address')
    return {
        'status': get_status,
        'label': get_localizer(request).translate(label),
        'id': 'postaladdress',
    }


def get_address_id(address):
    return u'%s, %s %s, %s' % (address['address'],
                               address['postalCode'],
                               address['locality'],
                               address['country'])


# @view_config(route_name='postaladdress', permission='edit',
#              renderer='templates/postaladdress-form.jinja2')
class PostalAddressView(BaseFormView):
    """
    Change user postal address
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = PostalAddress()
    route = 'postaladdress'

    buttons = (Button(name='save', title=_('Save')), )

    def get_addresses(self):
        postal_address = {}
        alternative_postal_address = {}
        postal_addresses = self.user.get_addresses()
        if len(postal_addresses) > 0:
            if postal_addresses[0]['type'] == 'official':
                postal_address = postal_addresses[0]
                if len(postal_addresses) > 1:
                    alternative_postal_address = postal_addresses[1]
            else:
                alternative_postal_address = postal_addresses[0]

        return (postal_address, alternative_postal_address)

    def appstruct(self):
        (postal_address, alternative_postal_address) = self.get_addresses()
        return alternative_postal_address

    def get_template_context(self):
        context = super(PostalAddressView, self).get_template_context()
        (postal_address, alternative_postal_address) = self.get_addresses()

        context.update({
            'postal_address': postal_address,
            'alternative_postal_address': alternative_postal_address,
            'contains_official_postal_address': postal_address is not {},
        })
        return context

    def before(self, form):
        allowed_countries_in_settings = self.request.registry.settings.get('allowed_countries')
        if allowed_countries_in_settings:
            allowed_countries = [l.split('=') for l in allowed_countries_in_settings.splitlines() if l]
        else:
            allowed_countries = [(c.alpha2, c.name) for c in pycountry.countries]

        form['country'].widget = widget.SelectWidget(values=[(code.strip(), country.strip()) for code, country in allowed_countries])

    def save_success(self, addressform):
        address = self.schema.serialize(addressform)
        address['verified'] = False
        address['type'] = 'alternative'

        addresses = self.user.get_addresses()
        if len(addresses) > 0 and addresses[0].get('type') == 'official':
            if len(addresses) == 1:
                addresses.append(address)
            else:
                addresses[1] = address
        else:
            addresses = [address]

        # update the session data
        self.user.set_addresses(addresses)
        try:
            self.user.save(self.request)
        except UserOutOfSync:
            self.sync_user()
        else:
            message = _('Changes saved.')
            self.request.session.flash(
                    get_localizer(self.request).translate(message),
                    queue='forms')
            self.request.stats.count('dashboard/postal_address_saved', 1)

    def failure(self, e):
        context = super(PostalAddressView, self).failure(e)

        context.update({'form_error': True})
        return context
