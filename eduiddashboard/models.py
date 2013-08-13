import colander
import translationstring

from .validators import PasswordValidator

_ = translationstring.TranslationStringFactory('eduiddashboard')


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    verified = colander.SchemaNode(colander.Boolean())


class Emails(colander.SequenceSchema):
    emails = Email()


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
