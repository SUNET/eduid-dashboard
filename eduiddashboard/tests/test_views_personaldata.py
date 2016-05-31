# -*- encoding: utf-8 -*-

from mock import patch

from eduiddashboard.testing import LoggedInRequestTests
from eduid_userdb.dashboard import UserDBWrapper as UserDB
from eduid_userdb.userdb import User

class PersonalDataFormTests(LoggedInRequestTests):

    formname = 'personaldataview-form'

    def test_personaldata_form(self):
        self.set_logged()
        response = self.testapp.get('/profile/personaldata/')
        form = response.forms[self.formname]
        form['givenName'].value = 'Fooo'
        form['surname'].value = 'Bar'
        form['displayName'].value = 'Mr Foo'
        response = form.submit('save')
        self.assertIn('Fooo', response.body)
        self.assertIn('Bar', response.body)
        self.assertIn('Mr Foo', response.body)


    def test_personaldata_form_with_userdb(self):
        self.set_logged()

        response = self.testapp.get('/profile/personaldata/')

        form = response.forms[self.formname]
        form['givenName'].value = 'Foo'
        form['surname'].value = 'Bar'
        form['displayName'].value = 'Mr Foo'

        with patch.object(UserDB, 'exists_by_field', clear=True):

            UserDB.exists_by_field.return_value = True

            response = form.submit('save')
            self.assertEqual(response.status, '200 OK')

        updated_user = self.dashboard_db.get_user_by_id(self.user.user_id)

        self.assertEqual(u'Foo', updated_user.given_name)
        self.assertEqual(u'Mr Foo', updated_user.display_name)
        self.assertEqual(u'Bar', updated_user.surname)
