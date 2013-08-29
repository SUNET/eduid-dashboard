import colander

from eduiddashboard.validators import EmailUniqueValidator


class BooleanMongo(colander.Boolean):

    def __init__(self, false_choices=('False', 'false', '', False),
                 true_choices=('True', 'true', True),
                 false_val=False,
                 true_val=True):
        super(BooleanMongo, self).__init__(false_choices, true_choices,
                                           false_val, true_val)


class Email(colander.MappingSchema):
    email = colander.SchemaNode(colander.String(),
                                validator=colander.All(colander.Email(),
                                                       EmailUniqueValidator())
                                )


class Person(colander.MappingSchema):
    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())
    screen_name = colander.SchemaNode(colander.String())
