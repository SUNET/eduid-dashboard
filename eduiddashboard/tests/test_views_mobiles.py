import json
from bson import ObjectId

from mock import patch

from eduid_userdb.dashboard import UserDBWrapper
from eduid_userdb.dashboard import DashboardUser
from eduiddashboard.testing import LoggedInRequestTests
from eduiddashboard.msgrelay import MsgRelay


class MobilesFormTests(LoggedInRequestTests):

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
                with patch.object(UserDBWrapper, 'exists_by_field', clear=True):
                    UserDBWrapper.exists_by_field.return_value = False
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
            with patch.object(UserDBWrapper, 'exists_by_field', clear=True):
                UserDBWrapper.exists_by_field.return_value = False
                response = form.submit('add')

                self.assertEqual(response.status, '200 OK')
                self.assertIn('alert-danger', response.body)
                self.assertIn('Invalid telephone number', response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

    def _remove_existant_mobile(self, n=1):
        return self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': n, 'action': 'remove'}
        )

    def test_remove_existant_mobile(self):
        self.set_logged()
        user = self.dashboard_db.get_user_by_id(self.user.user_id)
        mobiles_number = user.phone_numbers.count
        response = self._remove_existant_mobile()
        user_after = self.dashboard_db.get_user_by_id(self.user.user_id)
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')
        self.assertEqual(mobiles_number - 1, user_after.phone_numbers.count)

    def test_remove_primary_mobile(self):
        self.set_logged()

        old_user = self.userdb_new.get_user_by_id(self.user.user_id)
        old_primary_phone = old_user.phone_numbers.primary.number
        old_phone_count = len(old_user.phone_numbers.to_list())

        with patch.object(UserDBWrapper, 'exists_by_field', clear=True):
            UserDBWrapper.exists_by_field.return_value = False
            response = self._remove_existant_mobile(n=0)

            response_json = json.loads(response.body)
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response_json['result'], 'success')

            updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)
            updated_primary_phone = updated_user.phone_numbers.primary.number
            updated_phone_count = len(updated_user.phone_numbers.to_list())

            self.assertNotEqual(old_primary_phone, updated_primary_phone)
            self.assertTrue(updated_phone_count < old_phone_count)

    def test_remove_primary_mobile_and_set_other_verified_to_primary(self):
        self.set_logged()

        with patch.object(UserDBWrapper, 'exists_by_field', clear=True):
            UserDBWrapper.exists_by_field.return_value = True

            response = self.testapp.post(
                '/profile/mobiles-actions/',
                {'identifier': 0, 'action': 'remove'}
            )

            # If this test fail we'll get a PrimaryElementViolation
            # so an assertion for the correct HTTP response code is enough.
            self.assertEqual(response.status, '200 OK')

    def test_remove_not_existant_mobile(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user.user_id})[0]
        mobiles_number = len(userdb['mobile'])

        self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 10, 'action': 'remove'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user.user_id})[0]
        self.assertEqual(mobiles_number, len(userdb_after['mobile']))

    def test_verify_not_existing_mobile(self):
        self.set_logged()

        old_user = self.userdb_new.get_user_by_id(self.user.user_id)
        old_phones = old_user.phone_numbers.to_list_of_dicts()
        amount_of_phone_numbers = len(old_phones)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': amount_of_phone_numbers, 'action': 'verify'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)
        updated_phones = updated_user.phone_numbers.to_list_of_dicts()

        self.assertEqual(old_phones, updated_phones)

    def test_verify_not_existing_code(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user.user_id})[0]
        verified_mobile = userdb['mobile'][1]
        self.assertEqual(verified_mobile['verified'], False)
        self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 1, 'code': 'not_existing_code', 'action': 'verify'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user.user_id})[0]
        verified_mobile = userdb_after['mobile'][1]
        self.assertEqual(verified_mobile['verified'], False)

    def test_verify_existing_mobile(self):
        self.set_logged()
        user = self.dashboard_db.get_user_by_id(self.user.user_id)
        verified_mobile = user.phone_numbers.to_list()[1]
        self.assertFalse(verified_mobile.is_verified)
        self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': 1, 'code': '9d392c', 'action': 'verify'}
        )
        user = self.dashboard_db.get_user_by_id(self.user.user_id)
        verified_mobile = user.phone_numbers.to_list()[1]
        self.assertTrue(verified_mobile.is_verified)

    def test_setprimary_nonexistent_mobile(self):
        self.set_logged()

        old_user = self.userdb_new.get_user_by_id(self.user.user_id)

        old_phones = old_user.phone_numbers.to_list_of_dicts()
        amount_of_phone_numbers = len(old_phones)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': amount_of_phone_numbers, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)
        updated_phones = updated_user.phone_numbers.to_list_of_dicts()

        self.assertEqual(old_phones, updated_phones)

    def test_set_primary_not_verified_mobile(self):
        self.set_logged()
        index = 1

        old_user = self.userdb_new.get_user_by_id(self.user.user_id)
        old_primary_phone = old_user.phone_numbers.primary.number
        phone_to_test = old_user.phone_numbers.find('+34 6096096096')

        # Make sure that the phone number that we are about
        # to test if we can set as primary is not verified.
        self.assertEqual(phone_to_test.is_verified, False)

        # Make sure that the phone number that we are about
        # to test is not already set as primary.
        self.assertEqual(phone_to_test.is_primary, False)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': index, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'bad')

        updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)
        updated_primary_mobile = updated_user.phone_numbers.primary.number

        self.assertEqual(old_primary_phone, updated_primary_mobile)

    def test_setprimary_verified_mobile(self):
        self.set_logged()
        index = 2

        old_user = self.userdb_new.get_user_by_id(self.user.user_id)
        phone_to_test = old_user.phone_numbers.find('+34607507507')

        # Make sure that the phone number that we are
        # about to set as primary is actually verified.
        self.assertEqual(phone_to_test.is_verified, True)

        # Make sure that the phone number that we are about
        # to test is not already set as primary.
        self.assertEqual(phone_to_test.is_primary, False)

        response = self.testapp.post(
            '/profile/mobiles-actions/',
            {'identifier': index, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')

        updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)
        updated_phone_to_test = updated_user.phone_numbers.find('+34607507507')

        self.assertEqual(updated_phone_to_test.is_primary, True)

    def test_steal_verified_mobile(self):
        self.set_logged(email='johnsmith@example.org')

        response_form = self.testapp.get('/profile/mobiles/')

        form = response_form.forms[self.formname]

        mobile = '+34609609609'
        form['mobile'].value = mobile

        with patch.object(MsgRelay, 'mobile_validator', clear=True):
            MsgRelay.mobile_validator.return_value = True

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')

        old_user = self.dashboard_db.get_user_by_mail('johnsmith@example.com')
        self.assertIn(mobile, [mo.number for mo in old_user.phone_numbers.to_list()])

        new_user = self.dashboard_db.get_user_by_mail('johnsmith@example.org')
        self.assertIn(mobile, [mo.number for mo in new_user.phone_numbers.to_list()])

        # After adding the e-mail address to the user we're logged in as, make sure it is synced to
        # userdb even if there is no eduid-dashboard-amp around to do it
        self.sync_user_from_dashboard_to_userdb(self.logged_in_user.user_id)

        mobile_doc = self.db.verifications.find_one({
            'model_name': 'phone',
            'user_oid': ObjectId('901234567890123456789012'),
            'obj_id': mobile
        })

        with patch.object(MsgRelay, 'mobile_validator', clear=True):
            with patch.object(UserDBWrapper, 'exists_by_field', clear=True):
                UserDBWrapper.exists_by_field.return_value = False
                MsgRelay.mobile_validator.return_value = True

                response = self.testapp.post(
                    '/profile/mobiles-actions/',
                    {'identifier': 0, 'action': 'verify', 'code': mobile_doc['code']}
                )

                response_json = json.loads(response.body)
                self.assertEqual(response_json['result'], 'success')

        old_user = self.dashboard_db.get_user_by_mail('johnsmith@example.com')

        self.assertNotIn(mobile, [mo.number for mo in old_user.phone_numbers.to_list()])
