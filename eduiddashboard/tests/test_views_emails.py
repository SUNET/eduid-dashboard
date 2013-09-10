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

        self.assertIn('johnsmith@example.org', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith@example.org'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('johnsmith@example.org', response.body)
            self.assertIn('alert-error', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_not_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        form = response_form.forms[self.formname]

        form['mail'].value = 'user@example.com'
        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = False
            response = form.submit('verify')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('user@example.com', response.body)
            self.assertIn('alert-error', response.body)
            self.assertIn('This email is not registered', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertIn('johnsmith@example.org', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith@example.org'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('verify')
            self.assertEqual(response.status, '200 OK')
            self.assertIn('A new verification email has been sent to your'
                          ' account', response.body)
            self.assertIn('johnsmith@example.org', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_remove_not_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        form = response_form.forms[self.formname]

        form['mail'].value = 'user@example.com'

        response = form.submit('remove')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('user@example.com', response.body)
        self.assertIn('alert-error', response.body)
        self.assertIn("The email can't be found", response.body)
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_remove_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertIn('johnsmith@example.org', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith@example.org'

        response = form.submit('remove')
        self.assertEqual(response.status, '200 OK')
        self.assertIn('email has been removed,', response.body)
        self.assertNotIn('johnsmith@example.org', response.body)
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_setprimary_not_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        form = response_form.forms[self.formname]

        form['mail'].value = 'user@example.com'
        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = False
            response = form.submit('setprimary')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('user@example.com', response.body)
            self.assertIn('alert-error', response.body)
            self.assertIn('This email is not registered', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_setprimary_existant_email(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/emails/')

        self.assertIn('johnsmith@example.org', response_form.body)

        form = response_form.forms[self.formname]

        form['mail'].value = 'johnsmith@example.org'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('setprimary')
            self.assertEqual(response.status, '200 OK')
            self.assertIn('Your primary email was changed', response.body)

            checked_email_re = re.compile(
                r"<[^>]*type='radio'[^>]*"
                "value='johnsmith@example.org'[^>]*"
                "checked/>"
            )
            self.assertRegexpMatches(response.body, checked_email_re)

            self.assertIsNotNone(getattr(response, 'form', None))
