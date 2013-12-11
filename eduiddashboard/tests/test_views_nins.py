import json

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB


class NinsFormTests(LoggedInReguestTests):

    formname = 'ninsview-form'

    def test_logged_get(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.get('/profile/nins/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/nins/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_nin(self):
        self.set_logged(user='johnsmith@example.org')

        response_form = self.testapp.get('/profile/nins/')

        self.assertNotIn('johnsmith@example.info', response_form.body)

        form = response_form.forms[self.formname]
        nin = '200010100001'
        form['norEduPersonNIN'].value = nin
        with patch.object(UserDB, 'exists_by_filter', clear=True):

            UserDB.exists_by_filter.return_value = False

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn(nin, response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_not_valid_nin(self):
        self.set_logged(user='johnsmith@example.org')

        nin = '200010100001-'
        response_form = self.testapp.get('/profile/nins/')

        form = response_form.forms[self.formname]

        form['norEduPersonNIN'].value = nin
        with patch.object(UserDB, 'exists_by_filter', clear=True):

            UserDB.exists_by_filter.return_value = False
            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn(nin, response.body)
            self.assertIn('alert-error', response.body)
            self.assertIn('error-deformField', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_existant_nin(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/nins/')

        form = response_form.forms[self.formname]

        form['norEduPersonNIN'].value = '123456789012'

        with patch.object(UserDB, 'exists_by_filter', clear=True):

            UserDB.exists_by_filter.return_value = True

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('123456789012', response.body)
            self.assertIn('alert-error', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_not_existant_nin(self):
        self.set_logged(user='johnsmith@example.org')

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 50, 'action': 'verify'},
            status=404
        )

    def test_verify_existant_nin(self):
        self.set_logged()

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 0, 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'getcode')

    def test_remove_existant_verified_nin(self):
        self.set_logged()

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 0, 'action': 'remove'},
            status=200)

    def test_remove_existant_notverified_nin(self):
        self.set_logged()

        nins_before = self.db.verifications.find({
            'model_name': 'norEduPersonNIN',
            'user_oid': self.user['_id']
        }).count()

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 0, 'action': 'remove'},
            status=200)

        nins_after = self.db.verifications.find({
            'model_name': 'norEduPersonNIN',
            'user_oid': self.user['_id']
        }).count()

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(nins_before - 1, nins_after)

    def test_remove_not_existant_nin(self):
        self.set_logged(user='johnsmith@example.org')

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 24, 'action': 'remove'},
            status=404
        )
