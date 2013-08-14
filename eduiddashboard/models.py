import colander


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    verified = colander.SchemaNode(colander.Boolean(),
                                   read_only=True)


class Emails(colander.SequenceSchema):
    emails = Email()

class EmailsPerson(colander.MappingSchema):
    emails = Emails()

class Person(colander.MappingSchema):

    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())
