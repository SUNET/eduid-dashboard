import re

import pycountry

import colander
import deform

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.validators import (EmailUniqueValidator,
                                       EmailOrUsernameExistsValidator,
                                       ResetPasswordCodeExistsValidator,
                                       PasswordValidator,
                                       OldPasswordValidator,
                                       PermissionsValidator,
                                       NINUniqueValidator,
                                       NINReachableValidator,
                                       MobilePhoneUniqueValidator)

from eduiddashboard.widgets import permissions_widget


SEARCHER_ATTTRIBUTE_TYPES = [
    (u'mail', _('email')),
    (u'mobile', _('phone mobile number')),
    (u'norEduPersonNIN', _('NIN')),
]


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


class Email(colander.MappingSchema):
    mail = colander.SchemaNode(colander.String(),
                               validator=colander.All(colander.Email(),
                                                      EmailUniqueValidator()),
                               title=_('email'),
                               widget=deform.widget.TextInputWidget(mask=_('Email address')))


NINFormatValidator = colander.Regex(
    regex=re.compile(r'^(\d{8}|\d{6})(-|\ |)\d{4}$'),
    msg=_('The Swedish national identity number should be entered as yyyymmdd-xxxx')
)


def normalize_nin(nin):
    # Normalize nin, removing hyphen and whitespaces
    newnin = nin.replace(' ', '')
    newnin = newnin.replace('-', '')
    return nin


class NIN(colander.MappingSchema):
    """
        Allowed NIN input format:

        197801011234 (normalized form)
        19780101 1234
        19780101-1234
        780101-1234 (with 100year old guessing)
        7801011234 (with 100year old guessing)
        780101 1234 (with 100year old guessing)

    """
    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        title=_('Swedish national identity number'),
        validator=All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator(),
            NINReachableValidator()
        ),
        widget=deform.widget.TextInputWidget(mask=_('yyyymmdd-xxxx'))
    )


@colander.deferred
def preferred_language_widget(node, kw):
    request = kw.get('request')
    available_languages = request.registry.settings.get('available_languages')

    lang_choices = []
    for lang in available_languages:
        lang_obj = pycountry.languages.get(alpha2=lang)
        lang_choices.append((lang, lang_obj.name))

    return deform.widget.SelectWidget(values=lang_choices)


class Person(colander.MappingSchema):
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


class Passwords(colander.MappingSchema):

    old_password = colander.SchemaNode(colander.String(),
                                       title=_('Current password'),
                                       widget=deform.widget.PasswordWidget(size=20),
                                       validator=OldPasswordValidator())


class EmailResetPassword(colander.MappingSchema):

    email_or_username = colander.SchemaNode(
        colander.String(),
        title=_("Enter your email address or your eduID username"),
        validator=colander.All(
            EmailOrUsernameExistsValidator(),
        )
    )


class NINResetPassword(colander.MappingSchema):

    # norEduPersonNIN = colander.SchemaNode(
    #     colander.String(),
    #     title=_('personal identity number (NIN)'),
    #     validator=colander.All(
    #         colander.Regex(
    #             regex=re.compile('[0-9]{12}'),
    #             msg=_('The personal identity number consists of 12 digits')
    #         ),
    #         NINExistsValidator(),
    #     )
    # )
    email_or_username = colander.SchemaNode(
        colander.String(),
        title=_("Enter your email address or your eduID username"),
        validator=colander.All(
            EmailOrUsernameExistsValidator(),
        )
    )


class ResetPasswordEnterCode(colander.MappingSchema):

    code = colander.SchemaNode(
        colander.String(),
        title=_('Confirmation code'),
        validator=colander.All(
            ResetPasswordCodeExistsValidator(),
        )
    )


class ResetPasswordStep2(colander.MappingSchema):
    new_password = colander.SchemaNode(colander.String(),
                                       widget=deform.widget.PasswordWidget(size=20),
                                       validator=PasswordValidator())
    new_password_repeated = colander.SchemaNode(colander.String(),
                                                widget=deform.widget.PasswordWidget(size=20))

    def validator(self, node, data):
        if data['new_password'] != data['new_password_repeated']:
            raise colander.Invalid(node,
                                   _("Passwords don't match"))


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


class Mobile(colander.MappingSchema):
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

    text = colander.SchemaNode(colander.String(),
                               title=_('text'),
                               description=_('the exact match text for the '
                                             'attribute type selected for '
                                             'search')
                               )

    attribute_type = colander.SchemaNode(
        colander.String(),
        title=_('attribute type'),
        description=_('Select the attribute to search'),
        default='mail',
        widget=deform.widget.RadioChoiceWidget(
            values=SEARCHER_ATTTRIBUTE_TYPES,
            inline=True
        )
    )
