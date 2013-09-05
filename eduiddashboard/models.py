import re

import colander
import deform

from eduiddashboard.validators import PasswordValidator, old_password_validator

from eduiddashboard.i18n import TranslationString as _

from eduiddashboard.validators import EmailUniqueValidator


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


class Email(colander.MappingSchema):
    mail = colander.SchemaNode(colander.String(),
                               validator=colander.All(colander.Email(),
                                                      EmailUniqueValidator()),
                               title=_('email'))


class NIN(colander.MappingSchema):
    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        title=_('personal identity number (NIN)'),
        validator=colander.Regex(
            regex=re.compile('[0-9]{12}'),
            msg=_('The personal identity number consists of 12 digits')
        )
    )
    verified = colander.SchemaNode(BooleanMongo(), missing=False,
                                   title=_('verified'))
    active = colander.SchemaNode(BooleanMongo(), missing=False,
                                 title=_('active'))


class NINs(colander.SequenceSchema):
    NINs = NIN(title=_('personal identity numbers'))


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
                                    title=_('given name'))
    sn = colander.SchemaNode(colander.String(),
                             title=_('surname'))
    displayName = colander.SchemaNode(colander.String(),
                                      title=_('display name'))
    photo = colander.SchemaNode(colander.String(),
                                title=_('photo'),
                                description=_('A url link to your porsonal '
                                              'avatar'),
                                missing='')
    preferredLanguage = colander.SchemaNode(colander.String(),
                                            title=_('preferred language'),
                                            missing='',
                                            widget=preferred_language_widget)

    norEduPersonNIN = NINs(title=_('personal identity numbers'))


class Passwords(colander.MappingSchema):

    old_password = colander.SchemaNode(colander.String(),
                                       validator=old_password_validator)
    new_password = colander.SchemaNode(colander.String(),
                                       validator=PasswordValidator())
    new_password_repeated = colander.SchemaNode(colander.String())

    def validator(self, node, data):
        if data['new_password'] != data['new_password_repeated']:
            raise colander.Invalid(node,
                                   _("Both passwords don't match"))


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
