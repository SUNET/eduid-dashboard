import re

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB
from eduiddashboard.vccs import check_password, add_credentials


class PasswordFormTests(LoggedInReguestTests):

    formname = 'passwordsview-form'
    initial_password = 'old-password'

    def setUp(self, settings={}):
        super(PasswordFormTests, self).setUp(settings=settings)
        vccs_url = self.settings['vccs_url']
        add_credentials(vccs_url, 'xxx', self.initial_password, self.user)

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/passwords/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/passwords/')
        self.assertEqual(response.status, '302 Found')

    def test_add_credentials(self):
        vccs_url = self.settings['vccs_url']
        self.assertTrue(check_password(vccs_url, self.initial_password, self.user))
        new_password = 'new-password'
        add_credentials(vccs_url, self.initial_password, new_password, self.user)
        self.assertTrue(check_password(vccs_url, new_password, self.user))
        self.assertFalse(check_password(vccs_url, self.initial_password, self.user))

    def test_valid_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/passwords/')

        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password
        form['new_password'].value = 'new-password'
        form['new_password_repeated'].value = 'new-password'

        response = form.submit('save')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('Your changes was saved', response.body)
        self.assertNotIn('Old password do not match', response.body)
        self.assertNotIn("Both passwords don't match", response.body)

    def test_not_valid_old_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/passwords/')

        form = response_form.forms[self.formname]
        form['old_password'].value = 'nonexistingpassword'
        form['new_password'].value = 'newpassword'
        form['new_password_repeated'].value = 'newpassword'

        response = form.submit('save')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('Old password do not match', response.body)
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_not_valid_repeated_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/passwords/')

        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password
        form['new_password'].value = 'newpassword'
        form['new_password_repeated'].value = 'newpassword2'

        response = form.submit('save')

        self.assertEqual(response.status, '200 OK')
        self.assertIn("Both passwords don't match", response.body)
        self.assertIsNotNone(getattr(response, 'form', None))
