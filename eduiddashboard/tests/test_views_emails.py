import json
from bson import ObjectId
import re

from mock import patch

from eduiddashboard.userdb import UserDBWrapper as UserDB
from eduiddashboard.user import DashboardLegacyUser as OldUser
from eduiddashboard.testing import LoggedInRequestTests


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

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': 10, 'action': 'verify'}
            )

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
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        emails_number = len(userdb['mailAliases'])

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': 10, 'action': 'remove'}
            )
        userdb_after = self.db.profiles.find({'_id': self.user['_id']})[0]
        self.assertEqual(emails_number, len(userdb_after['mailAliases']))

    def test_setprimary_not_existant_email(self):
        self.set_logged()

        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]

        with self.assertRaises(IndexError):
            self.testapp.post(
                '/profile/emails-actions/',
                {'identifier': 10, 'action': 'setprimary'}
            )

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
        self.assertEqual(response_json['result'], 'ok')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = OldUser(old_user)

        self.assertNotIn(mail, [ma['email'] for ma in old_user.get_mail_aliases()])
