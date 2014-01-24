import unittest

import colander

from eduiddashboard.models import NINFormatValidator


class NINSchema(colander.MappingSchema):

    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        validator=colander.All(
            NINFormatValidator,
        ),
    )


class TestValidationNIN(unittest.TestCase):

    def setUp(self, settings={}):
        self.schema = NINSchema()

    def test_presentformat_form_ok(self):

        valid_nins = [
            '197801011234',
            '19780101 1234',
            '19780101-1234',
        ]
        for nin in valid_nins:
            deserialized = self.schema.deserialize({'norEduPersonNIN': nin})
            self.assertIn('norEduPersonNIN', deserialized)
            self.assertIsNotNone(deserialized.get('norEduPersonNIN'))

    def test_form_notok(self):

        not_valid_nins = [
            '197801011234-',
            '-197801011234',
            '19780101 123',
            '19780101 123a',
            '1978010a 123a',
            '1978010a 123',
            '19780101_234',
            '160101011234',

            '7801011234a',
            '780101 123a',
            '78010a 1234',
            '780101_1234',
            '780101123a',
            '780101-1234-',
            'a780101-1234',
            '78010112-34',
            '780101 123 4',
            'a780101-1234',
            '780101-1234',
            '7801011234',
        ]

        for nin in not_valid_nins:
            self.assertRaises(colander.Invalid,
                              self.schema.deserialize,
                              {'norEduPersonNIN': nin})
