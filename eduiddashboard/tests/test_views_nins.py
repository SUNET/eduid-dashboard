import json

from mock import patch

from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard.userdb import UserDB


class NinsFormTests(LoggedInReguestTests):

    formname = 'ninsview-form'

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/nins/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/nins/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_nin(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/nins/')

        self.assertNotIn('johnsmith@example.info', response_form.body)

        form = response_form.forms[self.formname]

        form['norEduPersonNIN'].value = '123123123123'
        with patch.object(UserDB, 'exists_by_filter', clear=True):

            UserDB.exists_by_filter.return_value = False

            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('123123123123', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_not_valid_nin(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/nins/')

        form = response_form.forms[self.formname]

        form['norEduPersonNIN'].value = '123 123 123'
        with patch.object(UserDB, 'exists_by_filter', clear=True):

            UserDB.exists_by_filter.return_value = False
            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('123 123 123', response.body)
            self.assertIn('alert-error', response.body)
            self.assertIn('The Swedish personal identity number consists of '
                          '12 digits', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_existant_nin(self):
        self.set_logged()

        response_form = self.testapp.get('/profile/nins/')

        self.assertIn('123456789012', response_form.body)

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
        self.set_logged()

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 123456789000, 'action': 'verify'},
            status=200
        )


    def test_remove_existant_verified_nin(self):
        self.set_logged()

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 0, 'action': 'remove'},
            status=409)

    def test_remove_existant_notverified_nin(self):
        self.set_logged()
        userdb = self.db.profiles.find({'_id': self.user['_id']})[0]
        nins_number = len(userdb['norEduPersonNIN'])

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 1, 'action': 'remove'},
            status=200)
        userdb_after = self.db.profiles.find_one({'_id': self.user['_id']})

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(nins_number - 1, len(userdb_after['norEduPersonNIN']))

    def test_remove_not_existant_nin(self):
        self.set_logged()

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 24, 'action': 'remove'},
            status=404
        )


class NinsFormTests2(LoggedInReguestTests):

    formname = 'ninsview-form'

    users = [{
        'mail': 'johnsmith@example.com',
        'norEduPersonNIN': [{
            'norEduPersonNIN': '210987654321',
            'verified': True,
            'active': False,
        }, {
            'norEduPersonNIN': '123456789012',
            'verified': False,
            'active': False,
        }, {
            'norEduPersonNIN': '123456789013',
            'verified': False,
            'active': True,
        }],
    }]

    def test_verify_existant_nin(self):
        self.set_logged()

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': 2, 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'getcode')
