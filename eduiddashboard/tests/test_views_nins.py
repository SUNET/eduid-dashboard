import json
from mock import patch
import unittest
from bson import ObjectId
from datetime import datetime

from eduiddashboard.userdb import UserDBWrapper
from eduiddashboard.user import DashboardLegacyUser as OldUser
from eduiddashboard.testing import LoggedInRequestTests

import logging
logger = logging.getLogger(__name__)


def return_true(*args, **kwargs):
    return True


class NinsFormTests(LoggedInRequestTests):

    formname = 'ninsview-form'

    #no_nin_user_email = 'johnsmith@example.org'
    #users = [{
    #    'mail': no_nin_user_email,
    #    #'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
    #    'norEduPersonNIN': []
    #}]


    def setUp(self):
        super(NinsFormTests, self).setUp()
        # these tests want the self.user user to not have a NIN
        self.no_nin_user_email = 'johnsmith@example.org'
        user = self.userdb.get_user_by_mail(self.no_nin_user_email)
        user.set_nins([])
        self.userdb.save(user)

    def test_logged_get(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.get('/profile/nins/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/nins/')
        self.assertEqual(response.status, '302 Found')

    def test_add_valid_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        response_form = self.testapp.get('/profile/nins/')
        response_form.mustcontain(self.formname)

        self.assertNotIn('johnsmith@example.info', response_form.body)

        form = response_form.forms[self.formname]
        nin = '200010100001'
        form['norEduPersonNIN'].value = nin

        from eduiddashboard.msgrelay import MsgRelay
        with patch.object(UserDBWrapper, 'exists_by_filter', clear=True):

            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):

                UserDBWrapper.exists_by_filter.return_value = False

                response = form.submit('add')

                self.assertEqual(response.status, '200 OK')
                self.assertIn(nin, response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_not_valid_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        nin = '200010100001-'
        response_form = self.testapp.get('/profile/nins/')

        form = response_form.forms[self.formname]

        form['norEduPersonNIN'].value = nin
        with patch.object(UserDBWrapper, 'exists_by_filter', clear=True):

            UserDBWrapper.exists_by_filter.return_value = False
            response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn(nin, response.body)
            self.assertIn('alert-danger', response.body)
            self.assertIn('error-deformField', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_existant_nin(self):
        from eduiddashboard.msgrelay import MsgRelay
        self.set_logged(email=self.no_nin_user_email)
        response_form = self.testapp.get('/profile/nins/')
        form = response_form.forms[self.formname]
        nin = '200010100001'
        # First we add a nin...
        with patch.object(UserDBWrapper, 'exists_by_filter', clear=True):
            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):
                UserDBWrapper.exists_by_filter.return_value = True
                form['norEduPersonNIN'].value = nin
                form.submit('add')
        # ...and then we try to add it again.
        with patch.object(UserDBWrapper, 'exists_by_filter', clear=True):
            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):
                UserDBWrapper.exists_by_filter.return_value = True
                form['norEduPersonNIN'].value = nin
                response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn(nin, response.body)
            self.assertIn('alert-danger', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_not_existant_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '197801011299 50', 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

    def test_verify_existant_nin(self):
        # Add a non-verified NIN to the user with no NINs
        email = self.no_nin_user_email
        user = self.userdb.get_user_by_mail(email)
        user.set_nins([{'number': '123456789050',
                        'verified': False,
                        'primary': True,
                       }])
        self.userdb.save(user)
        # Set up a pending verfication
        verification_data = {
            '_id': ObjectId(),
            'code': '123124',
            'model_name': 'norEduPersonNIN',
            'obj_id': '123456789050',
            'user_oid': user.get_id(),
            'timestamp': datetime.utcnow(),
            'verified': False,
        }
        self.db.verifications.insert(verification_data)

        self.set_logged(email)

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '123456789050  0', 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'getcode')

    @unittest.skip('Functionality temporary removed')
    def test_remove_existant_verified_nin(self):
        self.set_logged()

        self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '210987654321 0', 'action': 'remove'},
            status=200)

    @unittest.skip('Functionality temporary removed')
    def test_remove_existant_notverified_nin(self):
        self.set_logged()

        nins_before = self.db.verifications.find({
            'model_name': 'norEduPersonNIN',
            'user_oid': self.user.get_id()
        }).count()

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '123456789050 0', 'action': 'remove'},
            status=200)

        nins_after = self.db.verifications.find({
            'model_name': 'norEduPersonNIN',
            'user_oid': self.user.get_id()
        }).count()

        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'ok')
        self.assertEqual(nins_before - 1, nins_after)

    @unittest.skip('Functionality temporary removed')
    def test_remove_not_existant_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '210987654399 24', 'action': 'remove'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

    def test_steal_verified_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        response_form = self.testapp.get('/profile/nins/')

        form = response_form.forms[self.formname]
        nin = '197801011234'
        form['norEduPersonNIN'].value = nin

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
                
            response = form.submit('add')

        self.assertEqual(response.status, '200 OK')

        old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
        old_user = OldUser(old_user)

        nins_list = [x['number'] for x in old_user.get_nins()]
        self.assertIn(nin, nins_list)

        nin_doc = self.db.verifications.find_one({
            'model_name': 'norEduPersonNIN',
            'user_oid': ObjectId('901234567890123456789012'),
            'obj_id': nin
        })

        with patch.object(MsgRelay, 'get_postal_address', clear=True):
            MsgRelay.get_postal_address.return_value = {
                'Address2': u'StreetName 104',
                'PostalCode': u'74142',
                'City': u'STOCKHOLM',
                }
            with patch.object(MsgRelay, 'postal_address_to_transaction_audit_log'):
                MsgRelay.postal_address_to_transaction_audit_log.return_value = True

                response = self.testapp.post(
                    '/profile/nins-actions/',
                    {'identifier': '197801011234 0', 'action': 'verify', 'code': nin_doc['code']}
                )

            response_json = json.loads(response.body)
            self.assertEqual(response_json['result'], 'ok')

            old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
            old_user = OldUser(old_user)

            self.assertNotIn(nin, old_user.get_nins())


class NinWizardTests(LoggedInRequestTests):

    no_nin_user_email = 'johnsmith@example.org'

    mock_users_patches = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['197801011234']
    }, {
        'mail': no_nin_user_email,
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    def test_no_display_wizard(self):
        self.set_logged(email ='johnsmith@example.com')
        response = self.testapp.get('/profile/', status=200)
        self.assertNotIn('openwizard', response.body)

    def test_not_logged_not_display_wizard(self):
        """ Redirect to saml views if no logged session """
        self.testapp.get('/profile/nin-wizard/', status=302)

    def test_display_wizard(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.get('/profile/', status=200)
        response.mustcontain('openwizard')

    def test_get_wizard_nin(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.get('/profile/nin-wizard/', status=200)
        response.mustcontain('norEduPersonNIN')

    def test_step0_notvalid_nin(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 0,
            'norEduPersonNIN': 'a123a',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')

    def test_step0_valid_nin(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 0,
            'norEduPersonNIN': 'a123a',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')

    def test_step_storage(self):
        self.set_logged(email=self.no_nin_user_email)

        # Make sure the user doesn't already have a nin
        user = self.userdb_new.get_user_by_mail(self.no_nin_user_email)
        self.assertEqual(user.nins.to_list(), [])

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__'):
                CSRFTokenValidator.__call__.return_value = None
                self.testapp.post('/profile/nin-wizard/', {
                    'action': 'next_step',
                    'step': 0,
                    'norEduPersonNIN': '196701101234',
                    'csrf': '1234',
                }, status=200)
                response = self.testapp.get('/profile/', status=200)
                response.mustcontain('initial_card = 1')


class NinWizardStep1Tests(LoggedInRequestTests):

    no_nin_user_email = 'johnsmith@example.org'

    mock_users_patches = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['197801011234']
    }, {
        'mail': no_nin_user_email,
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    initial_verifications = [{
        '_id': ObjectId('234567890123456789012301'),
        'code': '1234',
        'model_name': 'norEduPersonNIN',
        'obj_id': '123412341234',
        'user_oid': ObjectId("901234567890123456789012"),
        'timestamp': datetime.utcnow(),
        'verified': False,
    }]

    def test_step1_valid_code(self):
        self.set_logged(email=self.no_nin_user_email)

        from eduiddashboard.msgrelay import MsgRelay

        with patch.object(MsgRelay, 'get_postal_address'):
            MsgRelay.get_postal_address.return_value = {
                'Address2': u'StreetName 103',
                'PostalCode': u'74141',
                'City': u'STOCKHOLM',
            }
            with patch.object(MsgRelay, 'postal_address_to_transaction_audit_log'):
                MsgRelay.postal_address_to_transaction_audit_log.return_value = True

                response = self.testapp.post('/profile/nin-wizard/', {
                    'action': 'next_step',
                    'step': 1,
                    'norEduPersonNIN': '12341234-1234',
                    'code': '1234',
                }, status=200)
                self.assertEqual(response.json['status'], 'ok')

    def test_step1_not_valid_code(self):
        self.set_logged(email=self.no_nin_user_email)
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 1,
            'norEduPersonNIN': '12341234-1234',
            'code': '1234asdf',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')
        self.assertIn('code', response.json['data'])
