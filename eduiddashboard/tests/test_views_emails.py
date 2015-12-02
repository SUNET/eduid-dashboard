import json
from bson import ObjectId
import re

from mock import patch

from eduid_userdb.dashboard import UserDBWrapper as UserDB
from eduid_userdb.dashboard import DashboardLegacyUser as OldUser
from eduiddashboard.testing import LoggedInRequestTests

from eduid_userdb.dashboard import DashboardUser


class MailsFormTests(LoggedInRequestTests):

    formname = 'emailsview-form'

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/emails/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/emails/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertNotIn('johnsmith@example.info', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith@example.info'
        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = False

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('johnsmith@example.info', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_not_valid_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        form = response_form.forms[self.formname]

        form['mail'].value = 'user@exa mple.com'
        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = False
            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('user@exa mple.com', response.body)
            self.assertIn('alert-danger', response.body)
            self.assertIn('Invalid email address', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertIn('johnsmith2@example.com', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith2@example.com'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('johnsmith2@example.com', response.body)
            self.assertIn('alert-danger', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_nonnormal_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertIn('johnsmith2@example.com', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'JohnSmith2@Example.com'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('johnsmith2@example.com', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_not_existant_email(self):
        self.set_logged()
        self.userdb.UserClass = DashboardUser

        old_user = self.userdb.get_user_by_id(self.user['_id'])

        # Make a post that attempts to verify a non-existant mail address,
        # so no change is expected in the database.
        response = self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': len(old_user.mail_addresses.to_list()), 'action': 'verify'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        # Check that mail addresses was not updated. Sort of redundant since
        # we checked that we got an out of sync condition above.
        updated_user = self.dashboard_db.get_user_by_id(self.user['_id'])

        old_addresses = old_user.mail_addresses.to_list_of_dicts()
        updated_addresses = updated_user.mail_addresses.to_list_of_dicts()

        self.assertEqual(old_addresses, updated_addresses)

    def test_verify_existant_email(self):
        self.set_logged()

        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': 0, 'action': 'verify'}
        )
        response_json = json.loads(response.body)

        self.assertEqual(response_json['result'], 'getcode')
        self.assertIn('Check your email inbox for',
                      response_json['message'])
        self.assertIn('for further instructions',
                      response_json['message'])

    def test_remove_existant_email(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        emails_number = len(userdb['mailAliases'])

        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': 0, 'action': 'remove'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')
        self.assertEqual(emails_number - 1, len(userdb_after['mailAliases']))

    def test_remove_not_existant_email(self):
        self.set_logged()
        self.userdb.UserClass = DashboardUser

        old_user = self.userdb.get_user_by_id(self.user['_id'])
        old_amount_of_addresses = len(old_user.mail_addresses.to_list_of_dicts())

        response = self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': old_amount_of_addresses, 'action': 'remove'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        updated_user = self.dashboard_db.get_user_by_id(self.user['_id'])
        updated_amount_of_addresses = len(updated_user.mail_addresses.to_list_of_dicts())

        self.assertEqual(old_amount_of_addresses, updated_amount_of_addresses)

    def test_setprimary_not_existant_email(self):
        self.set_logged()
        self.userdb.UserClass = DashboardUser

        old_user = self.userdb.get_user_by_id(self.user['_id'])
        # FFF from here
        old_amount_of_addresses = len(old_user.mail_addresses.to_list_of_dicts())
        old_primary_mail = old_user.mail_addresses.primary.email

        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': old_amount_of_addresses, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

        updated_user = self.dashboard_db.get_user_by_id(self.user['_id'])
        updated_primary_mail = updated_user.mail_addresses.primary.email

        self.assertEqual(old_primary_mail, updated_primary_mail)
        # FFF to here

    def test_setprimary_existant_email(self):
        self.set_logged()

        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': 0, 'action': 'setprimary'}
        )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')
        self.assertEqual(userdb_after['mail'], userdb_after['mailAliases'][0]['email'])

    def test_setprimary_not_verified_mail(self):
        self.set_logged()
        self.userdb.UserClass = DashboardUser
        mail_index = 2

        old_user = self.userdb.get_user_by_id(self.user['_id'])
        old_primary_mail = old_user.mail_addresses.primary.email
        mail_to_test = old_user.mail_addresses.find("johnsmith3@example.com")

        # Make sure that the mail address that we are about
        # to test if we can set as primary is not verified.
        self.assertEqual(mail_to_test.is_verified, False)

        # Make sure that the mail address that we are about
        # to test is not already set as primary.
        self.assertEqual(mail_to_test.is_primary, False)

        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': mail_index, 'action': 'setprimary'}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'bad')

        updated_user = self.dashboard_db.get_user_by_id(self.user['_id'])
        updated_primary_mail = updated_user.mail_addresses.primary.email

        self.assertEqual(old_primary_mail, updated_primary_mail)

    def test_steal_verified_mail(self):
        self.set_logged(email ='johnsmith@example.org')

        response_form = self.testapp.get('/profile/emails/')

        form = response_form.forms[self.formname]

        mail = 'johnsmith2@example.com'
        form['mail'].value = mail

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True
                
            response = form.submit('add')
            self.assertEqual(response.status, '200 OK')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = OldUser(old_user)

        self.assertIn(mail, [ma['email'] for ma in old_user.get_mail_aliases()])

        email_doc = self.db.verifications.find_one({
            'model_name': 'mailAliases',
            'user_oid': ObjectId('901234567890123456789012'),
            'obj_id': mail
        })

        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': 3, 'action': 'verify', 'code': email_doc['code']}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = OldUser(old_user)

        self.assertNotIn(mail, [ma['email'] for ma in old_user.get_mail_aliases()])

    def test_steal_verified_mail_from_ourself(self):
        self.set_logged(email='johnsmith@example.org')
        user = self.db.profiles.find_one({'_id': ObjectId('901234567890123456789012')})
        user = OldUser(user)
        mail = 'myuniqemail@example.info'

        response_form = self.testapp.get('/profile/emails/')

        self.assertNotIn(mail, response_form.body)

        form = response_form.forms[self.formname]
        form['mail'].value = mail

        # Try to steal the unique email address by submitting and verifying two
        # times that the user is the rightful owner of this email address.
        for i in range(0,2):

            with patch.object(UserDB, 'exists_by_field', clear=True):
                UserDB.exists_by_field.return_value = False

                response = form.submit('add')

                self.assertEqual(response.status, '200 OK')
                self.assertIn(mail, response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

            # Get the document that contains the code needed
            # to verify that the user owns the address.
            email_doc = self.db.verifications.find_one({
                'model_name': 'mailAliases',
                'user_oid': ObjectId(user.get_id()),
                'obj_id': mail
            })

            response = self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': 3, 'action': 'verify', 'code': email_doc['code']}
            )

            response_json = json.loads(response.body)
            self.assertEqual(response_json['result'], 'success')
