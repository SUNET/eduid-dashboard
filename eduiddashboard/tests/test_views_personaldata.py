# -*- encoding: utf-8 -*-

from eduiddashboard.testing import LoggedInRequestTests


class PersonalDataFormTests(LoggedInRequestTests):

    formname = 'personaldataview-form'

    def test_personaldata_form(self):
        self.set_logged()
        response = self.testapp.get('/profile/personaldata/')
        form = response.forms[self.formname]
        form['givenName'].value = 'Foo'
        form['sn'].value = 'Bar'
        form['displayName'].value = 'Mr Foo'
        response = form.submit('save')
        self.assertIn('Bar', response.body)
        self.assertIn('Mr Foo', response.body)
