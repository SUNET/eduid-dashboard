
import colander
from pyramid.security import Allow, Authenticated


class Person(colander.MappingSchema):
    __acl__ = [
        (Allow, Authenticated, 'edit')
    ]

    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
