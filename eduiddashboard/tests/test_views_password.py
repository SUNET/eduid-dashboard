from datetime import datetime
from mock import patch
from copy import deepcopy

from bson import ObjectId
import simplejson as json
import vccs_client
import pytz

from eduiddashboard.user import DashboardLegacyUser as OldUser
from eduiddashboard.testing import LoggedInRequestTests
from eduiddashboard import vccs
from eduiddashboard.vccs import (check_password, add_credentials, provision_credentials)

from eduid_userdb import Password

from eduid_userdb.testing import MockedUserDB as MUDB

import logging
log = logging.getLogger(__name__)


class FakeVCCSClient(vccs_client.VCCSClient):

    def __init__(self, fake_response=None):
        self.fake_response = fake_response

    def _execute_request_response(self, _service, _values):
        if self.fake_response is not None:
            return json.dumps(self.fake_response)

        fake_response = {}
        if _service == 'add_creds':
            fake_response = {
                'add_creds_response': {
                    'version': 1,
                    'success': True,
                },
            }
        elif _service == 'authenticate':
            fake_response = {
                'auth_response': {
                    'version': 1,
                    'authenticated': True,
                },
            }
        elif _service == 'revoke_creds':
            fake_response = {
                'revoke_creds_response': {
                    'version': 1,
                    'success': True,
                },
            }
        return json.dumps(fake_response)


class PasswordFormTests(LoggedInRequestTests):

    formname = 'passwordsview-form'
    initial_password = 'old-password'

    def setUp(self, settings={}):
        super(PasswordFormTests, self).setUp(settings=settings)
        vccs_url = self.settings['vccs_url']
        fake_vccs_client = FakeVCCSClient()
        mock_config = {
            'return_value': fake_vccs_client,
        }
        self.patcher = patch.object(vccs, 'get_vccs_client', **mock_config)
        self.patcher.start()
        provision_credentials(vccs_url, self.initial_password, self.user)

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/profile/security/')

        self.assertEqual(response.status, '200 OK')
        self.assertIn('start-password-change-form', response.forms)

    def test_notlogged_get(self):
        response = self.testapp.get('/profile/security/')
        self.assertEqual(response.status, '302 Found')

    def test_add_credentials(self):
        vccs_url = self.settings['vccs_url']
        self.assertTrue(check_password(vccs_url, self.initial_password, self.user))
        new_password = 'new-password'
        add_credentials(vccs_url, self.initial_password, new_password, self.user)
        self.assertTrue(check_password(vccs_url, new_password, self.user))

        with patch('eduiddashboard.vccs', clear=True):
            vccs.get_vccs_client.return_value = FakeVCCSClient(fake_response={
                'auth_response': {
                    'version': 1,
                    'authenticated': False,
                },
            })
            self.assertFalse(check_password(vccs_url, self.initial_password, self.user))

    def test_valid_current_password(self):
        self.set_logged()
        response = self.testapp.get('/profile/security/')
        form = response.forms['start-password-change-form']
        form_response = form.submit('submit')
        self.assertEqual(form_response.status, '302 Found')
        self.assertIn('idp.example.com', form_response.location)
        response_form = self.testapp.get('/profile/password-change/')
        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password
        self.add_to_session({'re-authn-ts': datetime.utcnow(),
                             'user': self.user})
        from eduiddashboard.validators import CSRFTokenValidator
        with patch.object(CSRFTokenValidator, '__call__', clear=True):

            CSRFTokenValidator.__call__.return_value = None
            response = form.submit('save')
        self.assertEqual(response.status, '302 Found')
        response = self.testapp.get(response.location)
        self.assertIn('Your password has been successfully updated',
                      response.body)
        self.assertNotIn('Old password do not match', response.body)
        self.assertNotIn("Both passwords don't match", response.body)

    def test_not_valid_current_password(self):
        self.set_logged()
        response_form = self.testapp.get('/profile/password-change/')
        form = response_form.forms[self.formname]
        form['old_password'].value = 'nonexistingpassword'
        self.add_to_session({'re-authn-ts': datetime.utcnow(),
                             'user': self.user})
        from eduiddashboard.validators import CSRFTokenValidator
        with patch.object(CSRFTokenValidator, '__call__', clear=True):
            CSRFTokenValidator.__call__.return_value = None
            with patch('eduiddashboard.vccs', clear=True):
                vccs.get_vccs_client.return_value = FakeVCCSClient(fake_response={
                    'auth_response': {
                        'version': 1,
                        'authenticated': False,
                    },
                })
                response = form.submit('save')
                self.assertEqual(response.status, '200 OK')
                self.assertIn('Current password is incorrect', response.body)
                self.assertIsNotNone(getattr(response, 'form', None))

    def test_password_form_entropy(self):
        self.set_logged()
        response = self.testapp.get('/profile/security/')
        response_form = self.testapp.get('/profile/password-change/')
        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password
        form['custom_password'].value = '0l8m vta8 j9lr'
        form['repeated_password'].value = form['custom_password'].value
        self.add_to_session({'re-authn-ts': datetime.utcnow(),
                             'user': self.user})
        from eduiddashboard.validators import CSRFTokenValidator
        with patch.object(CSRFTokenValidator, '__call__', clear=True):
            CSRFTokenValidator.__call__.return_value = None
            response = form.submit('save')
        self.assertEqual(response.status, '302 Found')
        response = self.testapp.get(response.location)
        self.assertIn('Your password has been successfully updated',
                      response.body)
        self.assertNotIn('Old password do not match', response.body)
        self.assertNotIn("Both passwords don't match", response.body)

    def test_password_form_entropy_notvalid(self):
        self.set_logged()
        response = self.testapp.get('/profile/security/')
        response_form = self.testapp.get('/profile/password-change/')
        form = response_form.forms[self.formname]
        form['old_password'].value = self.initial_password

        for password in [
            'april march',
            'April March',
            'meat with potatoes and bread',
            '123412341234',
            'asdfasdfasdf',
            'eduid',
            'aaaaaaaaaaaaa',
            'onetwothreefour',
        ]:
            form['custom_password'].value = password
            form['repeated_password'].value = form['custom_password'].value
            self.add_to_session({'re-authn-ts': datetime.utcnow(),
                                 'user': self.user})
            from eduiddashboard.validators import CSRFTokenValidator
            with patch.object(CSRFTokenValidator, '__call__', clear=True):
                CSRFTokenValidator.__call__.return_value = None
                response = form.submit('save')

            self.assertEqual(response.status, '200 OK')
            self.assertIn('The password complexity is too weak.',
                          response.body, msg='The entropy for {0} is bigger than required'.format(password))
            self.assertNotIn('Your password has been successfully updated',
                             response.body)

    def tearDown(self):
        super(PasswordFormTests, self).tearDown()
        self.patcher.stop()


FAKE_SESSION_INFO = {
    'authn_info': [('urn:oasis:names:tc:SAML:2.0:ac:classes:Password', [])],
    'ava': {'mail': ['johnsmith@example.com']},
    'came_from': 'http://profile.eduid.example.com:6544/profile/account-terminated/',
    'issuer': 'https://idp.example.com/simplesaml/saml2/idp/metadata.php',
    'not_on_or_after': 1417031214}


class TerminateAccountTests(LoggedInRequestTests):

    def test_reset_password_unterminates_account(self):
        email = 'johnsmith@example.com'
        # Set up a bunch of faked passwords to make sure they are all revoked
        user = self.dashboard_db.get_user_by_mail(email)
        for i in range(7):
            pw = Password(credential_id=ObjectId(),
                          salt=str(i) * 64,
                          application='dashboard_unittest',
                          )
            user.passwords.add(pw)
        self.dashboard_db.save(user)

        request = self.set_logged(email=email)
        response = self.testapp.get('/profile/security/')
        form = response.forms['terminate-account-form']

        # Verify the user has eight passwords and is NOT terminated at this point
        user = self.dashboard_db.get_user_by_mail(email)
        self.assertEqual(len(user.passwords.to_list_of_dicts()), 8)
        self.assertFalse(user.terminated)

        form_response = form.submit('submit')
        self.assertEqual(form_response.status, '302 Found')
        self.assertIn('idp.example.com', form_response.location)
        with patch('eduiddashboard.vccs.get_vccs_client'):
            from eduiddashboard.vccs import get_vccs_client
            get_vccs_client.return_value = FakeVCCSClient(fake_response={
                'revoke_creds_response': {
                    'version': 1,
                    'success': True,
                },
            })
            with patch('eduiddashboard.views.portal.send_termination_mail'):
                from eduiddashboard.views.portal import send_termination_mail
                send_termination_mail.return_value = None
                with patch('eduiddashboard.views.portal.logout_view'):
                    from eduiddashboard.views.portal import logout_view
                    logout_view.return_value = None
                    request.session['user'] = self.user
                    request.POST['RelayState'] = '/profile/account-terminated/'
                    request.context.propagate_user_changes = lambda x: None
                    from eduiddashboard.views.portal import account_termination_action
                    user = self.userdb.get_user_by_mail(email)
                    account_termination_action(request, FAKE_SESSION_INFO, user)

        # Verify the user doesn't have ANY passwords and IS terminated at this point
        user = self.dashboard_db.get_user_by_mail(email)
        self.assertEqual(len(user.passwords.to_list_of_dicts()), 0)
        self.assertTrue(user.terminated)

        # Do a password reset, which should resurrect the terminated user
        hash_code = '123456'
        date = datetime.now(pytz.utc)
        self.db.reset_passwords.insert({
            'email': email,
            'hash_code': hash_code,
            'mechanism': 'email',
            'created_at': date
        }, safe=True)
        response = self.testapp.get('/profile/reset-password/{0}/'.format(hash_code))
        self.assertIn('Please choose a new password for your eduID account', response.text)
        form = response.forms['resetpasswordstep2view-form']
        with patch('eduiddashboard.vccs.get_vccs_client'):
            from eduiddashboard.vccs import get_vccs_client
            get_vccs_client.return_value = FakeVCCSClient()
            form_resp = form.submit('reset')

        # Verify the user has a password and is NOT terminated again
        user = self.dashboard_db.get_user_by_mail(email)
        self.assertEqual(len(user.passwords.to_list_of_dicts()), 1)
        self.assertFalse(user.terminated)


TEST_USER = {
        '_id': ObjectId('012345678901234567890123'),
        'eduPersonPrincipalName': 'heffe-leffe',
        'givenName': 'John',
        'sn': 'Smith',
        'displayName': 'John Smith',
        'norEduPersonNIN': ['197801011234'],
        #'photo': 'https://pointing.to/your/photo',
        'preferredLanguage': 'en',
        'mail': 'johnnysmith1@example.org',
        'eduPersonEntitlement': [],
        #'modified_ts': datetime.utcnow(),
        'mobile': [{
            'mobile': '+46701234567',
            'verified': True,
            'primary': True,
        }],
        'mailAliases': [{
            'email': 'johnnysmith1@example.org',
            'verified': True,
        }, {
            'email': 'johnnysmith2@example.com',
            'verified': True,
        }, {
            'email': 'johnnysmith3@example.com',
            'verified': False,
        }]
    }

TEST_VERIFICATIONS = [{
    '_id': ObjectId('234567890123456789012301'),
    'code': '9d392d',
    'model_name': 'email',
    'obj_id': 'johnnysmith3@example.com',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.utcnow(),
    'verified': False,
}]


def return_true(*args, **kwargs):
    return True


class MockedUserDB(MUDB):

    test_users = {
        'johnnysmith1@example.com': TEST_USER,
    }


class ResetPasswordFormTests(LoggedInRequestTests):

    formname = 'passwordsview-form'
    initial_password = 'old-password'
    MockedUserDB = MockedUserDB
    initial_verifications = TEST_VERIFICATIONS

    def setUp(self, settings={}):
        super(ResetPasswordFormTests, self).setUp(settings=settings, std_user='johnnysmith1@example.org')
        vccs_url = self.settings['vccs_url']
        fake_vccs_client = FakeVCCSClient()
        mock_config = {
            'return_value': fake_vccs_client,
        }
        self.patcher = patch.object(vccs, 'get_vccs_client', **mock_config)
        self.patcher.start()
        add_credentials(vccs_url, 'xxx', self.initial_password, self.user)

    def test_reset_password(self):
        response_form = self.testapp.get('/profile/reset-password/email/')

        form = response_form.forms['resetpasswordemailview-form']

        form['email_or_username'].value = 'notexistingmail@foodomain.com'
        response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')

        form['email_or_username'].value = 'johnnysmith3@example.com'
        response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')

        self.db.reset_passwords.remove()
        form['email_or_username'].value = '0701234567'
        from eduiddashboard.msgrelay import MsgRelay
        with patch.multiple(MsgRelay, nin_validator=return_true, nin_reachable=return_true,
                            nin_reset_password=return_true):
            response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')
        reset_passwords_after = list(self.db.reset_passwords.find())
        self.assertEqual(len(reset_passwords_after), 1)
        self.db.reset_passwords.remove()

        for email in self.user['mailAliases']:
            if not email['verified']:
                continue
            form['email_or_username'].value = email['email']
            response = form.submit('reset')
            self.assertEqual(response.status, '302 Found')
        reset_passwords_after = list(self.db.reset_passwords.find())
        self.assertEqual(len(reset_passwords_after), 1)

    def test_reset_password_mina(self):
        response_form = self.testapp.get('/profile/reset-password/mina/')

        form = response_form.forms['resetpasswordninview-form']

        form['email_or_username'].value = 'notexistingmail@foodomain.com'
        response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')

        self.db.reset_passwords.remove()
        form['email_or_username'].value = 'johnnysmith3@example.com'
        from eduiddashboard.msgrelay import MsgRelay
        with patch.multiple(MsgRelay, nin_validator=return_true, nin_reachable=return_true,
                            nin_reset_password=return_true):
            response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')

        self.db.reset_passwords.remove()
        form['email_or_username'].value = '0701234567'
        with patch.multiple(MsgRelay, nin_validator=return_true, nin_reachable=return_true,
                            nin_reset_password=return_true):
            response = form.submit('reset')
        self.assertEqual(response.status, '302 Found')
        reset_passwords_after = list(self.db.reset_passwords.find())
        self.assertEqual(len(reset_passwords_after), 1)

        form['email_or_username'].value = 'notexistingmail@foodomain'
        response = form.submit('reset')
        self.assertIn('Valid input formats are:', response.body)

    def test_reset_password_code(self):
        hash_code = '123456'
        date = datetime.now(pytz.utc)
        self.db.reset_passwords.insert({
            'email': 'johnnysmith3@example.com',
            'hash_code': hash_code,
            'mechanism': 'email',
            'created_at': date
        }, safe=True)
        response = self.testapp.get('/profile/reset-password/{0}/'.format(hash_code))
        self.assertIn('Please choose a new password for your eduID account', response.text)

    def test_reset_password_invalid_code(self):
        hash_code = '123456'
        wrong_code = '654321'
        self.db.reset_passwords.insert({
            'email': 'johnnysmith3@example.com',
            'hash_code': hash_code,
            'mechanism': 'email',
            'verified': False,
        }, safe=True)
        response = self.testapp.get('/profile/reset-password/{0}/'.format(wrong_code))
        self.assertEqual(response.status, '302 Found')

    def test_reset_password_invalid_input(self):
        response_form = self.testapp.get('/profile/reset-password/email/')

        form = response_form.forms['resetpasswordemailview-form']

        form['email_or_username'].value = 'notexistingmail@foodomain'
        response = form.submit('reset')
        self.assertIn('Valid input formats are:', response.body)

        form['email_or_username'].value = '1601010000'
        response = form.submit('reset')
        self.assertIn('Valid input formats are:', response.body)

        form['email_or_username'].value = '+14'
        response = form.submit('reset')
        self.assertIn('Valid input formats are:', response.body)

    def tearDown(self):
        super(ResetPasswordFormTests, self).tearDown()
        self.patcher.stop()
