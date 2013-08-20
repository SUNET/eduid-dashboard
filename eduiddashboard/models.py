import colander
import translationstring

from .validators import PasswordValidator

_ = translationstring.TranslationStringFactory('eduiddashboard')

from eduiddashboard.widgets import MongoCheckboxWidget


class BooleanMongo(colander.Boolean):

    def __init__(self, false_choices=('False', 'false', '', False),
                 true_choices=('True', 'true', True),
                 false_val=False,
                 true_val=True):
        super(BooleanMongo, self).__init__(false_choices, true_choices,
                                           false_val, true_val)


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    verified = colander.SchemaNode(BooleanMongo(),
                                   widget=MongoCheckboxWidget(),
                                   missing=False)
    primary = colander.SchemaNode(BooleanMongo(), default=False,
                                  widget=MongoCheckboxWidget(),
                                  missing=False)


class Emails(colander.SequenceSchema):
    emails = Email()


class EmailsPerson(colander.MappingSchema):

    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email(),
                                missing='')
    emails = Emails()


class Person(colander.MappingSchema):
    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())


class Passwords(colander.MappingSchema):

    old_password = colander.SchemaNode(colander.String())
    new_password = colander.SchemaNode(colander.String(),
                                       validator=PasswordValidator())
    new_password_repeated = colander.SchemaNode(colander.String())

    def validator(self, node, data):
        if data['new_password'] != data['new_password_repeated']:
            raise colander.Invalid(node,
                                   _("Both passwords don't match"))
