## Postal address forms

from deform import widget
from pyramid.view import view_config

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import PostalAddress
from eduiddashboard.views import BaseFormView


@view_config(route_name='postaladdress', permission='edit',
             renderer='templates/passwords-form.jinja2')
class PostalAddressView(BaseFormView):
    """
    Change user postal address
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = PostalAddress()
    route = 'postaladdress'

    def before(self, form):
        allowed_countries = self.request.registry.settings.get('allowed_countries').split(',')
        form['country'].widget = widget.SelectWidget(values=[(c.strip(), c.strip()) for c in allowed_countries])

    def submit_success(self, addressform):
        address = self.schema.serialize(addressform)
        # update the session data
        self.request.session['user'].update(address)

        # Insert the new user object
        self.request.db.profiles.update({
            '_id': self.user['_id'],
        }, self.user, safe=True)

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

        self.request.session.flash(_('Your changes was saved, please, wait '
                                     'before your changes are distributed '
                                     'through all applications'),
                                   queue='forms')
