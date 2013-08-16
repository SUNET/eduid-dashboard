import colander


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    verified = colander.SchemaNode(colander.Boolean(false_choices=('false',),
                                                    true_choices=('true',),
                                                    false_val='false',
                                                    true_val='true'),
                                   missing=False)
    primary = colander.SchemaNode(colander.Boolean(), default=False,
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
