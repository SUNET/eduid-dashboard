import json
from mock import patch
from bson import ObjectId
from datetime import datetime

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


class NinWizardTests(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['123456789013']
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    def test_no_display_wizard(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/profile/', status=200)
        self.assertNotIn('openwizard', response.body)

    def test_not_logged_not_display_wizard(self):
        """ Redirect to saml views if no logged session """
        self.testapp.get('/profile/nin-wizard/', status=302)

    def test_display_wizard(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.get('/profile/', status=200)
        self.assertIn('openwizard', response.body)

    def test_get_wizard_nin(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.get('/profile/nin-wizard/', status=200)
        self.assertIn('norEduPersonNIN', response.body)

    def test_step0_notvalid_nin(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 0,
            'norEduPersonNIN': 'a123a',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')

    def test_step0_valid_nin(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 0,
            'norEduPersonNIN': 'a123a',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')

    def test_step_storage(self):
        self.set_logged(user='johnsmith@example.org')
        self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 0,
            'norEduPersonNIN': '12341234-1234',
        }, status=200)
        response = self.testapp.get('/profile/', status=200)
        self.assertIn('initial_card = 1', response.body)


class NinWizardStep1Tests(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['123456789013']
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    initial_verifications = [{
        '_id': ObjectId('234567890123456789012301'),
        'code': '1234',
        'model_name': 'norEduPersonNIN',
        'obj_id': '12341234-1234',
        'user_oid': ObjectId("901234567890123456789012"),
        'timestamp': datetime.utcnow(),
        'verified': False,
    }]

    def test_step1_valid_code(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 1,
            'norEduPersonNIN': '12341234-1234',
            'code': '1234',
        }, status=200)
        self.assertEqual(response.json['status'], 'ok')

    def test_step1_not_valid_code(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 1,
            'norEduPersonNIN': '12341234-1234',
            'code': '1234asdf',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')
        self.assertIn('text', response.json['text'])
