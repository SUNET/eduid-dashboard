import colander


class Password(colander.MappingSchema):
    id = colander.SchemaNode(colander.String())
    salt = colander.SchemaNode(colander.String())


class Passwords(colander.SequenceSchema):
    passwords = Password()


class Person(colander.MappingSchema):
    _id = colander.SchemaNode(colander.String())
    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    passwords = Passwords()
