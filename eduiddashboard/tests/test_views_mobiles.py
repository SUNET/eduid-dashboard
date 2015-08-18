import json
from bson import ObjectId

from mock import patch

from eduid_am.userdb import UserDB
from eduid_am.user import User
from eduiddashboard.testing import LoggedInReguestTests
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

    def test_add_existent_mobile(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/mobiles/')

        form = response_form.forms[self.formname]

        form['mobile'].value = '+34609609609'

        response = form.submit('add')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('alert-danger', response.body)
        self.assertIsNotNone(getattr(response, 'form', None))

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
                self.assertIn('alert-danger', response.body)
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
        self.assertEqual(response_json['result'], 'success')
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
        userdb_before = self.db.profiles.find_one({'_id': self.user['_id']})
        verified_list_before = [m['verified'] for m in userdb_before['mobile']]

        response = self.testapp.post(
                '/profile/mobiles-actions/',
                {'identifier': 10, 'action': 'verify'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        userdb_after = self.db.profiles.find_one({'_id': self.user['_id']})
        verified_list_after = [m['verified'] for m in userdb_after['mobile']]
        self.assertEqual(verified_list_before, verified_list_after)

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

    def test_setprimary_nonexistent_mobile(self):
        self.set_logged()
        userdb_before = self.db.profiles.find_one({'_id': self.user['_id']})

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 10, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        userdb_after = self.db.profiles.find_one({'_id': self.user['_id']})
        self.assertEqual(userdb_before['mobile'], userdb_after['mobile'])

    def test_set_primary_not_verified_mobile(self):
        self.set_logged()
        index = 1
        userdb_before = self.db.profiles.find_one({'_id': self.user['_id']})
        not_verified_mobile = userdb_before['mobile'][index]

        # Make sure that the mobile that we are about
        # to test if we can set as primary is not verified.
        self.assertEqual(not_verified_mobile['verified'], False)

        if not_verified_mobile.has_key('primary'):
            self.assertEqual(not_verified_mobile['primary'], False)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': index, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'bad')

        userdb_after = self.db.profiles.find_one({'_id': self.user['_id']})
        not_primary_mobile = userdb_after['mobile'][index]

        if not_verified_mobile.has_key('primary'):
            self.assertEqual(not_primary_mobile['primary'], False)

    def test_setprimary_verified_mobile(self):
        self.set_logged()
        index = 0
        userdb_before = self.db.profiles.find_one({'_id': self.user['_id']})
        verified_mobile = userdb_before['mobile'][index]

        # Make sure that the mobile that we are about
        # to set as primary is actually verified.
        self.assertEqual(verified_mobile['verified'], True)

        if verified_mobile.has_key('primary'):
            self.assertEqual(verified_mobile['primary'], False)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': index, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')

        userdb_after = self.db.profiles.find_one({'_id': self.user['_id']})
        primary_mobile = userdb_after['mobile'][index]

        self.assertEqual(primary_mobile['primary'], True)

    def test_steal_verified_mobile(self):
        self.set_logged(user='johnsmith@example.org')

        response_form = self.testapp.get('/profile/mobiles/')

        form = response_form.forms[self.formname]

        mobile = '+34609609609'
        form['mobile'].value = mobile

        with patch.object(MsgRelay, 'mobile_validator', clear=True):
            MsgRelay.mobile_validator.return_value = True
                
            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = User(old_user)

        self.assertIn(mobile, [mo['mobile'] for mo in old_user.get_mobiles()])

        mobile_doc = self.db.verifications.find_one({
            'model_name': 'mobile',
            'user_oid': ObjectId('901234567890123456789012'),
            'obj_id': mobile
        })

        with patch.object(MsgRelay, 'mobile_validator', clear=True):
            with patch.object(UserDB, 'exists_by_field', clear=True):
                UserDB.exists_by_field.return_value = False
                MsgRelay.mobile_validator.return_value = True

                response = self.testapp.post(
                    '/profile/mobiles-actions/',
                    {'identifier': 0, 'action': 'verify', 'code': mobile_doc['code']}
                )

                response_json = json.loads(response.body)
                self.assertEqual(response_json['result'], 'success')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = User(old_user)

        self.assertNotIn(mobile, [mo['mobile'] for mo in old_user.get_mobiles()])
