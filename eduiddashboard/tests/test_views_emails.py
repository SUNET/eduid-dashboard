import json
import re

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB


class MailsFormTests(LoggedInReguestTests):

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
            self.assertIn('alert-error', response.body)
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
            self.assertIn('alert-error', response.body)
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
        self.assertEqual(response_json['result'], 'ok')
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
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(userdb_after['mail'], userdb_after['mailAliases'][0]['email'])
