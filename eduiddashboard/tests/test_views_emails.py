import json
import pprint
from bson import ObjectId

from mock import patch

from eduid_userdb.dashboard import UserDBWrapper as UserDB
from eduiddashboard.testing import LoggedInRequestTests

import logging
logger = logging.getLogger(__name__)


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

        old_user = self.userdb_new.get_user_by_id(self.user['_id'])

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

        old_user = self.userdb_new.get_user_by_id(self.user['_id'])
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

        old_user = self.userdb_new.get_user_by_id(self.user['_id'])
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
        mail_index = 2

        old_user = self.userdb_new.get_user_by_id(self.user['_id'])
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
        mail_to_steal = 'johnsmith2@example.com'

        self.set_logged(email ='johnsmith@example.org')

        orig_user = self.userdb_new.get_user_by_mail(mail_to_steal)

        response_form = self.testapp.get('/profile/emails/')
        form = response_form.forms[self.formname]
        form['mail'].value = mail_to_steal

        logger.debug(('-=-' * 30) + "\n\n")
        foo_user = self.userdb_new.get_user_by_id(self.logged_in_user.user_id)
        logger.debug('Stealing user BEFORE submitting form:\n{!s}\n\n\n'.format(pprint.pformat(foo_user.to_dict())))

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('add')
            self.assertEqual(response.status, '200 OK')

        # After adding the e-mail address to the user we're logged in as, make sure it is synced to
        # userdb even if there is no eduid-dashboard-amp around to do it
        self.sync_user_from_dashboard_to_userdb(self.logged_in_user.user_id)

        logger.debug(('-=-' * 30) + "\n\n")
        foo_user = self.userdb_new.get_user_by_id(self.logged_in_user.user_id)
        logger.debug('Stealing user AFTER submitting form:\n{!s}\n\n\n'.format(pprint.pformat(foo_user.to_dict())))

        # Make sure that merely claiming the mail_to_steal did not result in a changed ownership
        owner_now = self.userdb_new.get_user_by_mail(mail_to_steal)
        self.assertEqual(orig_user.user_id, owner_now.user_id)
        self.assertEqual(owner_now.user_id, ObjectId('012345678901234567890123'))

        # Find the verification code
        email_doc = self.db.verifications.find_one({
            'model_name': 'mailAliases',
            'user_oid': ObjectId('901234567890123456789012'),
            'obj_id': mail_to_steal
        })

        # Post the verification code to prove ownership of mail_to_steal
        response = self.testapp.post(
            '/profile/emails-actions/',
            {'identifier': 3, 'action': 'verify', 'code': email_doc['code']}
        )

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'success')

        # Verify the e-mail address `mail' is NO LONGER owned by the orig_user (after a sync of both users to the userdb)
        self.sync_user_from_dashboard_to_userdb(orig_user.user_id)
        self.sync_user_from_dashboard_to_userdb(self.logged_in_user.user_id)
        owner_now = self.userdb_new.get_user_by_mail(mail_to_steal)
        self.assertNotEqual(orig_user.user_id, owner_now.user_id)

    def test_steal_verified_mail_from_ourself(self):
        self.set_logged(email='johnsmith@example.org')
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
                'user_oid': ObjectId(self.logged_in_user.user_id),
                'obj_id': mail
            })

            self.sync_user_from_dashboard_to_userdb(self.logged_in_user.user_id)

            response = self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': 3, 'action': 'verify', 'code': email_doc['code']}
            )

            response_json = json.loads(response.body)
            self.assertEqual(response_json['result'], 'success')
