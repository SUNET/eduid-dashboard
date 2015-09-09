import json
from mock import patch, Mock
import unittest
from bson import ObjectId
from datetime import datetime

from eduid_am.userdb import UserDB
from eduid_am.user import User
from eduiddashboard.testing import LoggedInReguestTests


def return_true(*args, **kwargs):
    return True


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

        from eduiddashboard.msgrelay import MsgRelay
        with patch.object(UserDB, 'exists_by_filter', clear=True):

            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):

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
            self.assertIn('alert-danger', response.body)
            self.assertIn('error-deformField', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_add_existant_nin(self):
        from eduiddashboard.msgrelay import MsgRelay
        self.set_logged(user='johnsmith@example.org')
        response_form = self.testapp.get('/profile/nins/')
        form = response_form.forms[self.formname]
        nin = '200010100001'
        # First we add a nin...
        with patch.object(UserDB, 'exists_by_filter', clear=True):
            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):
                UserDB.exists_by_filter.return_value = True
                form['norEduPersonNIN'].value = nin
                form.submit('add')
        # ...and then we try to add it again.
        with patch.object(UserDB, 'exists_by_filter', clear=True):
            with patch.multiple(MsgRelay, nin_validator=return_true,
                                nin_reachable=return_true):
                UserDB.exists_by_filter.return_value = True
                form['norEduPersonNIN'].value = nin
                response = form.submit('add')

            self.assertEqual(response.status, '200 OK')
            self.assertIn(nin, response.body)
            self.assertIn('alert-danger', response.body)
            self.assertIsNotNone(getattr(response, 'form', None))

    def test_verify_not_existant_nin(self):
        self.set_logged(user='johnsmith@example.org')

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '197801011299 50', 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

    def test_verify_existant_nin(self):
        self.set_logged()

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '123456789050  0', 'action': 'verify'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'getcode')

    def test_verify_existant_nin_by_mobile(self):
        ''' '''
        self.set_logged(user='johnsmith@example.org')
        user = self.db.profiles.find_one({'mail': 'johnsmith@example.org'})
        from eduid_am.user import User
        user = User(user)
        self.assertEqual(len(user.get_nins()), 0)

        # First we add a nin...
        nin = '200010100001'

        response_form = self.testapp.get('/profile/nins/')
        form = response_form.forms[self.formname]
        from eduiddashboard.msgrelay import MsgRelay
        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            form['norEduPersonNIN'].value = nin
            form.submit('add')

        # and then we verify it
        self.testapp.get('/profile/nins/')
        from eduiddashboard.views import nins
        with patch.object(nins, 'validate_nin_by_mobile', clear=True):
            nins.validate_nin_by_mobile.return_value = {
                'success': True,
                'message': u'Ok',
                }
            with patch.object(User, 'retrieve_address', clear=True):
                User.retrieve_address.return_value = None

                response = self.testapp.post(
                    '/profile/nins-actions/',
                    {'identifier': nin + '  0', 'action': 'verify_mb'}
                )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['message'], 'Ok')
        user = self.db.profiles.find_one({'mail': 'johnsmith@example.org'})
        user = User(user)
        self.assertEqual(len(user.get_nins()), 1)
        self.assertEqual(user.get_nins()[0], nin)

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
        self.assertEqual(response_json['result'], 'success')
        self.assertEqual(nins_before - 1, nins_after)

    @unittest.skip('Functionality temporary removed')
    def test_remove_not_existant_nin(self):
        self.set_logged(user='johnsmith@example.org')

        response = self.testapp.post(
            '/profile/nins-actions/',
            {'identifier': '210987654399 24', 'action': 'remove'}
        )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['result'], 'out_of_sync')

    def test_steal_verified_nin(self):
        self.set_logged(user='johnsmith@example.org')

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
        old_user = User(old_user)

        self.assertIn(nin, old_user.get_nins())

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
            self.assertEqual(response_json['result'], 'success')

            old_user = self.db.profiles.find_one({'_id': ObjectId('012345678901234567890123')})
            old_user = User(old_user)

            self.assertNotIn(nin, old_user.get_nins())


class NinWizardTests(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['197801011234']
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    def test_no_display_wizard(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/profile/', status=200)
        response.mustcontain('data-openwizard="False"')

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

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            MsgRelay.nin_reachable = Mock(return_value=True)
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__', clear=True):
    
                CSRFTokenValidator.__call__.return_value = None
                self.testapp.post('/profile/nin-wizard/', {
                    'action': 'next_step',
                    'step': 0,
                    'norEduPersonNIN': '197412041234',
                    'csrf': '12345',
                }, status=200)
                response = self.testapp.get('/profile/', status=200)
                response.mustcontain('data-datakey="197412041234"')
                self.assertEqual(MsgRelay.nin_reachable.call_count, 1)

    def test_step_storage2(self):
        self.set_logged(user='johnsmith@example.org')

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__', clear=True):
    
                CSRFTokenValidator.__call__.return_value = None
                self.testapp.post('/profile/nin-wizard/', {
                    'action': 'next_step',
                    'step': 0,
                    'norEduPersonNIN': '197412041236',
                    'csrf': '12345',
                }, status=200)
                response = self.testapp.get('/profile/', status=200)
                response.mustcontain('data-datakey="197412041236"')

    def test_resend_code(self):
        self.set_logged(user='johnsmith@example.org')

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            MsgRelay.nin_reachable = Mock(return_value=True)
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__', clear=True):
    
                CSRFTokenValidator.__call__.return_value = None
                response = self.testapp.post('/profile/nin-wizard/', {
                    'action': 'resendcode',
                    'step': 1,
                    'code': '',
                    'norEduPersonNIN': '197412041236',
                    'csrf': '12345',
                }, status=200)

                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(MsgRelay.nin_reachable.call_count, 1)

    def test_resend_code_bad_nin(self):
        self.set_logged(user='johnsmith@example.org')

        from eduiddashboard.msgrelay import MsgRelay

        with patch.multiple(MsgRelay, nin_validator=return_true,
                            nin_reachable=return_true):
            MsgRelay.nin_reachable = Mock(return_value=True)
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__', clear=True):
    
                CSRFTokenValidator.__call__.return_value = None
                response = self.testapp.post('/profile/nin-wizard/', {
                    'action': 'resendcode',
                    'step': 1,
                    'code': '',
                    'norEduPersonNIN': '19741236',
                    'csrf': '12345',
                }, status=200)

                self.assertEqual(response.json['status'], 'error')
                self.assertEqual(MsgRelay.nin_reachable.call_count, 0)


class NinWizardStep1Tests(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': ['197801011234']
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': ['urn:mace:eduid.se:role:admin'],
        'norEduPersonNIN': []
    }]

    initial_verifications = [{
        '_id': ObjectId('234567890123456789012301'),
        'code': '1234',
        'model_name': 'norEduPersonNIN',
        'obj_id': '197001010000',
        'user_oid': ObjectId("901234567890123456789012"),
        'timestamp': datetime.utcnow(),
        'verified': False,
    }]

    def test_step1_valid_code(self):
        self.set_logged(user='johnsmith@example.org')

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
                    'norEduPersonNIN': '19700101-0000',
                    'code': '1234',
                }, status=200)
                self.assertEqual(response.json['status'], 'success')

    def test_step1_not_valid_code(self):
        self.set_logged(user='johnsmith@example.org')
        response = self.testapp.post('/profile/nin-wizard/', {
            'action': 'next_step',
            'step': 1,
            'norEduPersonNIN': '19700101-0000',
            'code': '1234asdf',
        }, status=200)
        self.assertEqual(response.json['status'], 'failure')
        self.assertIn('code', response.json['data'])

    def test_step0_after_step1_same_nin(self):
        self.set_logged(user='johnsmith@example.org')

        from eduiddashboard.msgrelay import MsgRelay

        with patch.object(MsgRelay, 'get_postal_address'):
            MsgRelay.get_postal_address.return_value = {
                'Address2': u'StreetName 103',
                'PostalCode': u'74141',
                'City': u'STOCKHOLM',
            }
            with patch.multiple(MsgRelay,
                                postal_address_to_transaction_audit_log=return_true,
                                nin_validator=return_true,
                                nin_reachable=return_true):
                from eduiddashboard.validators import CSRFTokenValidator
                with patch.object(CSRFTokenValidator, '__call__', clear=True):

                    CSRFTokenValidator.__call__.return_value = None

                    resp_step1 = self.testapp.post('/profile/nin-wizard/', {
                        'action': 'next_step',
                        'step': 1,
                        'norEduPersonNIN': '197001010000',
                        'code': '1234',
                        'csrf': '12345',
                    }, status=200)
                    self.assertEqual(resp_step1.json['status'], 'success')

                    resp_step0 = self.testapp.post('/profile/nin-wizard/', {
                        'action': 'next_step',
                        'step': 0,
                        'norEduPersonNIN': '19700101-0000',
                        'csrf': '12345',
                    }, status=200)
                    self.assertEqual(resp_step0.json['status'], 'failure')

    def test_step0_after_step1_different_nin(self):
        self.set_logged(user='johnsmith@example.org')

        from eduiddashboard.msgrelay import MsgRelay

        with patch.object(MsgRelay, 'get_postal_address'):
            MsgRelay.get_postal_address.return_value = {
                'Address2': u'StreetName 103',
                'PostalCode': u'74141',
                'City': u'STOCKHOLM',
            }
            with patch.multiple(MsgRelay,
                                postal_address_to_transaction_audit_log=return_true,
                                nin_validator=return_true,
                                nin_reachable=return_true):
                from eduiddashboard.validators import CSRFTokenValidator
                with patch.object(CSRFTokenValidator, '__call__', clear=True):

                    CSRFTokenValidator.__call__.return_value = None

                    resp_step1 = self.testapp.post('/profile/nin-wizard/', {
                        'action': 'next_step',
                        'step': 1,
                        'norEduPersonNIN': '19700101-0000',
                        'code': '1234',
                        'csrf': '12345',
                    }, status=200)
                    self.assertEqual(resp_step1.json['status'], 'success')

                    resp_step0 = self.testapp.post('/profile/nin-wizard/', {
                        'action': 'next_step',
                        'step': 0,
                        'norEduPersonNIN': '19700101-0001',
                        'csrf': '12345',
                    }, status=200)
                    self.assertEqual(resp_step0.json['status'], 'success')
