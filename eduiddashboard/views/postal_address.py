## Postal address forms

from deform import widget
import pycountry
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import PostalAddress
from eduiddashboard.views import BaseFormView


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

    buttons = ('add', 'verify', 'remove',)
    bootstrap_form_style = 'form-inline'

    def appstruct(self):
        return {}

    def get_template_context(self):
        context = super(PostalAddressView, self).get_template_context()
        context.update({
            'postal_addresses': self.user.get('postalAddresses', []),
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

        addresses = self.user.get('postalAddresses', [])
        addresses.append(address)

        # update the session data
        self.user['postalAddresses'] = addresses

        # do the save staff
        self.request.db.profiles.find_and_modify({
            '_id': self.user['_id'],
        }, {
            '$push': {
                'postalAddresses': addresses,
            }
        }, safe=True)

        # update the session data
        self.context.propagate_user_changes(self.user)

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
