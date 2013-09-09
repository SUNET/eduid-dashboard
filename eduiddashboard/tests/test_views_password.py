import re

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB
from eduiddashboard.vccs import check_password, add_credentials


class PasswordFormTests(LoggedInReguestTests):

    formname = 'passwordsview-form'

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/passwords/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/passwords/')
        self.assertEqual(response.status, '302 Found')

    def test_add_credentials(self):
        new_pwd = 'new_pwd'
        vccs_url = self.settings['vccs_url']
        add_credentials(vccs_url, 'xxx', new_pwd, self.user)
        self.assertTrue(check_password(vccs_url, new_pwd, self.user))

    # def test_add_valid_password(self):
    #     # XXX: To implement
    #     self.set_logged()

    #     response_form = self.testapp.get('/passwords/')

    #     self.assertNotIn('johnsmith@example.info', response_form.body)

    #     form = response_form.forms[self.formname]

    #     form['old_password'].value = 'oldpassword'

    #     with patch.object(UserDB, 'exists_by_field', clear=True):

    #         UserDB.exists_by_field.return_value = False

    #         response = form.submit('add')

    #         self.assertEqual(response.status, '200 OK')
    #         self.assertIn('johnsmith@example.info', response.body)
    #         self.assertIsNotNone(getattr(response, 'form', None))
