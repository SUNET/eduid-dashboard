import json
from mock import patch, Mock
import unittest
from bson import ObjectId
from datetime import datetime

from eduid_userdb.dashboard import UserDBWrapper
from eduid_userdb.dashboard import DashboardLegacyUser as OldUser
from eduid_userdb.element import PrimaryElementViolation
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

        response_form.mustcontain('input type="text" name="norEduPersonNIN"')

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
                        'primary': False,
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

    def test_verify_existant_nin_by_mobile(self):
        ''' '''
        email = self.no_nin_user_email
        self.set_logged(email)
        user = self.userdb.get_user_by_mail(email)

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
            with patch.object(OldUser, 'retrieve_address', clear=True):
                OldUser.retrieve_address.return_value = None

                response = self.testapp.post(
                    '/profile/nins-actions/',
                    {'identifier': nin + '  0', 'action': 'verify_mb'}
                )
        response_json = json.loads(response.body)
        self.assertEqual(response_json['message'], 'Ok')
        user = self.db.profiles.find_one({'mail': email})
        user = OldUser(user)
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
            old_user = OldUser(old_user)

            self.assertNotIn(nin, old_user.get_nins())


class NinsFormTestsDisableMM(LoggedInRequestTests):

    formname = 'ninsview-form'

    def setUp(self):
        disable_mm = {'enable_mm_verification': 'false'}
        super(NinsFormTestsDisableMM, self).setUp(settings=disable_mm)
        # these tests want the self.user user to not have a NIN
        self.no_nin_user_email = 'johnsmith@example.org'
        user = self.userdb.get_user_by_mail(self.no_nin_user_email)
        user.set_nins([])
        self.userdb.save(user)

    def test_add_valid_nin(self):
        self.set_logged(email=self.no_nin_user_email)

        response_form = self.testapp.get('/profile/nins/')
        response_form.mustcontain(self.formname)

        self.assertIn('ninsview-formNoMM', response_form.body)
        self.assertNotIn('johnsmith@example.info', response_form.body)
        self.assertNotIn('You can access your governmental inbox using',
                         response_form.body)
