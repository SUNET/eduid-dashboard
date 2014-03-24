import re

import colander
import deform

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.preparers import EmailNormalizer
from eduiddashboard.validators import (EmailUniqueValidator,
                                       PasswordValidator,
                                       OldPasswordValidator,
                                       PermissionsValidator,
                                       NINReachableValidator,
                                       NINUniqueValidator,
                                       MobilePhoneUniqueValidator,
                                       CSRFTokenValidator)

from eduiddashboard.widgets import permissions_widget


SEARCHER_ATTTRIBUTE_TYPES = [
    (u'mail', _('email')),
    (u'mobile', _('phone mobile number')),
    (u'norEduPersonNIN', _('national identity number')),
]


@colander.deferred
def csrf_token(node, kw):
    request = kw.get('request')
    token = request.session.get_csrf_token()
    return token


class CSRFTokenSchema(colander.MappingSchema):
    csrf = colander.SchemaNode(
        colander.String(),
        widget=deform.widget.HiddenWidget(),
        validator=CSRFTokenValidator(),
        default=csrf_token,
    )


class BooleanMongo(colander.Boolean):

    def __init__(self, false_choices=('False', 'false', '', False),
                 true_choices=('True', 'true', True),
                 false_val=False,
                 true_val=True):
        super(BooleanMongo, self).__init__(false_choices, true_choices,
                                           false_val, true_val)


class All_StopOnFirst(colander.All):

    def __call__(self, node, value):
        for validator in self.validators:
            try:
                validator(node, value)
            except colander.Invalid as e:
                raise colander.Invalid(node, e.msg)


class Email(CSRFTokenSchema):
    mail = colander.SchemaNode(colander.String(),
                               preparer=EmailNormalizer(),
                               validator=colander.All(colander.Email(),
                                                      EmailUniqueValidator()),
                               title=_('email'),
                               widget=deform.widget.TextInputWidget(mask=_('Email address')))


NINFormatValidator = colander.Regex(
    regex=re.compile(r'^(18|19|20)\d{2}(0[1-9]|1[0-2])\d{2}[-\s]?\d{4}$'),
    msg=_('The Swedish national identity number should be entered as yyyymmddnnnn')
)


def normalize_nin(nin):
    # Normalize nin, removing hyphen and whitespaces
    newnin = nin.replace(' ', '')
    newnin = newnin.replace('-', '')
    return newnin


class NIN(CSRFTokenSchema):
    """
        Allowed NIN input format:

        197801011234 (normalized form)
        19780101 1234
        19780101-1234
    """
    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        title=_('Swedish national identity number'),
        validator=All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator(),
            NINReachableValidator()
        ),
        widget=deform.widget.TextInputWidget(mask=_('yyyymmddnnnn'))
    )


@colander.deferred
def preferred_language_widget(node, kw):
    request = kw.get('request')
    lang_choices = request.registry.settings['available_languages'].items()
    return deform.widget.SelectWidget(values=lang_choices)


class Person(CSRFTokenSchema):
    givenName = colander.SchemaNode(colander.String(),
                                    readonly=True,
                                    title=_('Given name'))
    sn = colander.SchemaNode(colander.String(),
                             title=_('Surname'))
    displayName = colander.SchemaNode(colander.String(),
                                      title=_('Display name'))
    preferredLanguage = colander.SchemaNode(colander.String(),
                                            title=_('Preferred language'),
                                            missing='',
                                            widget=preferred_language_widget)


@colander.deferred
def password_readonly(node, kw):
    request = kw.get('request')
    return request.session.get('last_generated_password')


class Passwords(CSRFTokenSchema):

    old_password = colander.SchemaNode(
        colander.String(),
        title=_('Current password'),
        widget=deform.widget.PasswordWidget(size=20),
        validator=OldPasswordValidator())

    use_custom_password = colander.SchemaNode(
        colander.Boolean(),
        widget=deform.widget.CheckboxWidget(),
        title=_('Use my own password'),
        missing='false')

    suggested_password = colander.SchemaNode(
        colander.String(),
        title=_('Suggested password'),
        widget=deform.widget.TextInputWidget(
            readonly=True,
            css_class='suggested-password'
        ),
        missing=password_readonly)

    custom_password = colander.SchemaNode(
        colander.String(),
        title=_('Custom password'),
        widget=deform.widget.PasswordWidget(
            size=20,
            css_class='custom-password'),
        validator=PasswordValidator(),
        missing='')

    repeated_password = colander.SchemaNode(
        colander.String(),
        title=_('Repeat the password'),
        widget=deform.widget.PasswordWidget(
            size=20,
            css_class='custom-password'),
        missing='')


class EmailResetPassword(CSRFTokenSchema):

    email_or_username = colander.SchemaNode(
        colander.String(),
        title=""
    )


class NINResetPassword(CSRFTokenSchema):
    email_or_username = colander.SchemaNode(
        colander.String(),
        title=""
    )


class ResetPasswordStep2(CSRFTokenSchema):
    use_custom_password = colander.SchemaNode(
        colander.Boolean(),
        widget=deform.widget.CheckboxWidget(),
        title=_('Use my own password'),
        missing='false')

    suggested_password = colander.SchemaNode(
        colander.String(),
        title=_('Suggested password'),
        widget=deform.widget.TextInputWidget(
            readonly=True,
            css_class='suggested-password'
        ),
        missing=password_readonly)

    custom_password = colander.SchemaNode(colander.String(),
                                          widget=deform.widget.PasswordWidget(
                                              size=20,
                                              css_class='custom-password'
                                          ),
                                          validator=PasswordValidator(),
                                          title=_("New Password"),
                                          missing='')
    repeated_password = colander.SchemaNode(colander.String(),
                                            widget=deform.widget.PasswordWidget(
                                                size=20,
                                                css_class='custom-password'),
                                            title=_("Confirm New Password"),
                                            missing='')

    def validator(self, node, data):
        if data['custom_password'] != data['repeated_password']:
            raise colander.Invalid(node,
                                   _("Passwords doesn't match"))


@colander.deferred
def postal_address_default_country(node, kw):
    request = kw.get('request')
    default_location = request.registry.settings.get('default_country_location')
    return default_location


class PostalAddress(colander.MappingSchema):
    address = colander.SchemaNode(colander.String(), title=_('Address'))
    locality = colander.SchemaNode(colander.String(), title=_('City'))
    postalCode = colander.SchemaNode(colander.String(), title=_('Postal code'),
                                     validator=colander.Length(min=5, max=6))
    country = colander.SchemaNode(colander.String(), title=_('Country'),
                                  default=postal_address_default_country)


class Mobile(CSRFTokenSchema):
    mobile = colander.SchemaNode(colander.String(),
                                 validator=colander.All(
                                     colander.Regex(
                                         r'^\+\d{10,20}$|^07[0236]\d{7}$',
                                         msg=_('Invalid telephone number. It must be a valid Swedish number, or written using international notation, starting with "+" and followed by 10-20 digits.'),
                                     ),
                                     MobilePhoneUniqueValidator()
                                 ),
                                 title=_('mobile'),
                                 widget=deform.widget.TextInputWidget(mask=_('Mobile phone number')))


class Permissions(colander.Schema):
    eduPersonEntitlement = colander.SchemaNode(colander.List(),
                                               title='',
                                               validator=PermissionsValidator(),
                                               missing=[],
                                               default=[],
                                               widget=permissions_widget)


class UserSearcher(colander.MappingSchema):
    query = colander.SchemaNode(colander.String(),
                                description=_('Search for users'),
                                title=_('query'),
                                widget=deform.widget.TextInputWidget())
