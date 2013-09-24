import re

import colander
import deform

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.validators import (EmailUniqueValidator,
                                       EmailExistsValidator,
                                       PasswordValidator,
                                       OldPasswordValidator,
                                       PermissionsValidator,
                                       NINUniqueValidator)

from eduiddashboard.widgets import permissions_widget


SEARCHER_ATTTRIBUTE_TYPES = [
    (u'mail', _('email')),
    (u'mobile', _('phone mobile number')),
    (u'norEduPersonNIN', _('NIN')),
]

POSTAL_ADDRESS_TYPES = [
    (u'home', _('Home address')),
    (u'work', _('Work address')),
]


class BooleanMongo(colander.Boolean):

    def __init__(self, false_choices=('False', 'false', '', False),
                 true_choices=('True', 'true', True),
                 false_val=False,
                 true_val=True):
        super(BooleanMongo, self).__init__(false_choices, true_choices,
                                           false_val, true_val)


class Email(colander.MappingSchema):
    mail = colander.SchemaNode(colander.String(),
                               validator=colander.All(colander.Email(),
                                                      EmailUniqueValidator()),
                               title=_('email'))


class NIN(colander.MappingSchema):
    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        title=_('personal identity number (NIN)'),
        validator=colander.All(
            colander.Regex(
                regex=re.compile('[0-9]{12}'),
                msg=_('The personal identity number consists of 12 digits')
            ),
            NINUniqueValidator()
        )
    )


@colander.deferred
def preferred_language_widget(node, kw):
    request = kw.get('request')
    languages = request.registry.settings.get('available_languages')
    lang_choices = []
    for lang in languages:
        lang_choices.append((lang, _(lang)))

    return deform.widget.RadioChoiceWidget(values=lang_choices)


class Person(colander.MappingSchema):
    givenName = colander.SchemaNode(colander.String(),
                                    readonly=True,
                                    title=_('given name'))
    sn = colander.SchemaNode(colander.String(),
                             title=_('surname'))
    displayName = colander.SchemaNode(colander.String(),
                                      title=_('display name'))
    photo = colander.SchemaNode(colander.String(),
                                title=_('photo'),
                                description=_('A url link to your personal '
                                              'avatar'),
                                missing='')
    preferredLanguage = colander.SchemaNode(colander.String(),
                                            title=_('preferred language'),
                                            missing='',
                                            widget=preferred_language_widget)


class Passwords(colander.MappingSchema):

    old_password = colander.SchemaNode(colander.String(),
                                       widget=deform.widget.PasswordWidget(size=20),
                                       validator=OldPasswordValidator())
    new_password = colander.SchemaNode(colander.String(),
                                       widget=deform.widget.PasswordWidget(size=20),
                                       validator=PasswordValidator())
    new_password_repeated = colander.SchemaNode(colander.String(),
                                                widget=deform.widget.PasswordWidget(size=20))

    def validator(self, node, data):
        if data['new_password'] != data['new_password_repeated']:
            raise colander.Invalid(node,
                                   _("Both passwords don't match"))


class ResetPassword(colander.MappingSchema):

    email = colander.SchemaNode(colander.String(),
                                validator=colander.All(
                                    colander.Email(),
                                    EmailExistsValidator(),
                                ),
                                title=_("Enter your email address"))


class ResetPasswordStep2(colander.MappingSchema):
    new_password = colander.SchemaNode(colander.String(),
                                       widget=deform.widget.PasswordWidget(size=20),
                                       validator=PasswordValidator())
    new_password_repeated = colander.SchemaNode(colander.String(),
                                                widget=deform.widget.PasswordWidget(size=20))

    def validator(self, node, data):
        if data['new_password'] != data['new_password_repeated']:
            raise colander.Invalid(node,
                                   _("Both passwords don't match"))


class PostalAddress(colander.MappingSchema):
    type = colander.SchemaNode(colander.String(),
                               title=_('type'),
                               missing='registered',
                               validator=colander.OneOf([k for k, v in POSTAL_ADDRESS_TYPES]),
                               widget=deform.widget.SelectWidget(values=POSTAL_ADDRESS_TYPES))
    address = colander.SchemaNode(colander.String(), title=_('address'))
    locality = colander.SchemaNode(colander.String(), title=_('locality'))
    postalCode = colander.SchemaNode(colander.String(), title=_('postal code'),
                                     validator=colander.Length(min=5, max=6))
    country = colander.SchemaNode(colander.String(), title=_('country'))


class Mobile(colander.MappingSchema):
    mobile = colander.SchemaNode(colander.String(),
                                 validator=colander.Regex(
                                    r'^\+[\d ]+$',
                                    msg=_('Invalid telephone number. It must be written using international notation, starting with "+".'),
                                 ),
                                 title=_('mobile'))


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
