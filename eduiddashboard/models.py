import colander


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    verified = colander.SchemaNode(colander.Boolean())


class AlternativeEmails(colander.Sequence):
    emails = Email()


class Person(colander.MappingSchema):

    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())
