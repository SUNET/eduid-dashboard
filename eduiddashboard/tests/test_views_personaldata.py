# -*- encoding: utf-8 -*-

import json
from bson import ObjectId
import re

from mock import patch

from eduid_am.userdb import UserDB
from eduid_am.user import User
from eduiddashboard.testing import LoggedInReguestTests


class PersonalDataFormTests(LoggedInReguestTests):

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
