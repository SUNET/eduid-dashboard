import json

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB
from eduiddashboard.msgrelay import MsgRelay


class MobilesFormTests(LoggedInReguestTests):

    formname = 'mobilesview-form'

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/mobiles/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/mobiles/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_mobile(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/mobiles/')

        form = response_form.forms[self.formname]

        for good_value in ('+34678455654', '0720123456'):
            form['mobile'].value = good_value

            with patch.object(MsgRelay, 'mobile_validator', clear=True):
                with patch.object(UserDB, 'exists_by_field', clear=True):
                    UserDB.exists_by_field.return_value = False
                    MsgRelay.mobile_validator.return_value = True

                    response = form.submit('add')

                    self.assertEqual(response.status, '200 OK')
                    self.assertIsNotNone(getattr(response, 'form', None))
            if not good_value.startswith('+'):
                country_code = self.settings['default_country_code']
                if good_value.startswith('0') and len(good_value) > 6:
                    good_value = country_code + good_value[1:]
                else:
                    good_value = country_code + good_value

            self.assertIn(good_value, response.body)
            self.assertIsNotNone(self.db.verifications.find_one({
                'obj_id': good_value, 'verified': False},
            ))

    def test_add_not_valid_mobile(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/mobiles/')

        form = response_form.forms[self.formname]

        for bad_value in ('not_a_number', '545455', '+555555', '0770123456'):
            form['mobile'].value = bad_value
            with patch.object(UserDB, 'exists_by_field', clear=True):
                UserDB.exists_by_field.return_value = False
                response = form.submit('add')

                self.assertEqual(response.status, '200 OK')
                self.assertIn('alert-error', response.body)
                self.assertIn('Invalid telephone number', response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

    def test_remove_existant_mobile(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        mobiles_number = len(userdb['mobile'])

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 0, 'action': 'remove'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(mobiles_number - 1, len(userdb_after['mobile']))

    def test_remove_not_existant_mobile(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        mobiles_number = len(userdb['mobile'])

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/mobiles-actions/',
                {'identifier': 10, 'action': 'remove'}
            )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        self.assertEqual(mobiles_number, len(userdb_after['mobile']))

    def test_verify_not_existing_mobile(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_list = [m['verified'] for m in userdb['mobile']]

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/mobiles-actions/',
                {'identifier': 10, 'action': 'verify'}
            )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_list_after = [m['verified'] for m in userdb_after['mobile']]
        self.assertEqual(verified_list, verified_list_after)

    def test_verify_not_existing_code(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_mobile = userdb['mobile'][1]
        self.assertEqual(verified_mobile['verified'], False)
        self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 1, 'code': 'not_existing_code', 'action': 'verify'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_mobile = userdb_after['mobile'][1]
        self.assertEqual(verified_mobile['verified'], False)

    def test_verify_existing_mobile(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_mobile = userdb['mobile'][1]
        self.assertEqual(verified_mobile['verified'], False)
        self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 1, 'code': '9d392c', 'action': 'verify'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        verified_mobile = userdb_after['mobile'][1]
        self.assertEqual(verified_mobile['verified'], True)
