import json

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB


class PostalAddressFormTests(LoggedInReguestTests):

    formname = 'postaladdressview-form'

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/postaladdress/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/postaladdress/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_address(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/postaladdress/')

        form = response_form.forms[self.formname]

        form['type'].value = 'home'
        form['address'].value = 'SVEN NILSSON 10'
        form['locality'].value = 'STOCKHOLM'
        form['country'].value = 'SE'
        with patch.object(UserDB, 'exists_by_field', clear=True):
            UserDB.exists_by_field.return_value = False

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('SVEN NILSSON 10', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_not_valid_address(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/postaladdress/')

        form = response_form.forms[self.formname]
        bad_values = [
            {'type': 'not_existing_type',  # bad type
             'address': 'Foo',
             'locality': 'Bar',
             'country': 'SE',
             'postalCode': '12345',
            },
            {'type': 'home',
             'address': 'Foo',
             'locality': 'Bar',
             'country': 'SE',
             'postalCode': '123456789',  # too long
            },
        ]

        for bad_value in bad_values:
            for key, value in bad_value.items():
                if hasattr(form[key], 'options'):
                    # we change the options attribute in following sentence
                    # to check the validation in the post request and not 
                    # in the form[key] = value sentence
                    form[key].options = [(value, value)]
                form[key] = value
            with patch.object(UserDB, 'exists_by_field', clear=True):
                UserDB.exists_by_field.return_value = False
                response = form.submit('add')

                self.assertEqual(response.status, '200 OK')
                self.assertIn('alert-error', response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

    def test_remove_existant_address(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        addresses_number = len(userdb['postalAddress'])

        response = self.testapp.post(
            '/profile/postaladdress-actions/',
            {'identifier': 0, 'action': 'remove'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(addresses_number - 1, len(userdb_after['postalAddress']))

    def test_remove_not_existant_address(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        addresses_number = len(userdb['postalAddress'])

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/postaladdress-actions/',
                {'identifier': 10, 'action': 'remove'}
            )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        self.assertEqual(addresses_number, len(userdb_after['postalAddress']))
