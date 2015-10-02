from os import path
import datetime
from copy import deepcopy

from mock import patch

import unittest

from webtest import TestApp, TestRequest

from pyramid.interfaces import ISessionFactory, IDebugLogger
from pyramid.security import remember
from pyramid.testing import DummyRequest, DummyResource
from pyramid import testing

import pymongo
from bson import ObjectId

from eduid_userdb import UserDB
from eduid_userdb.dashboard import DashboardLegacyUser as OldUser, DashboardUserDB
from eduid_userdb.testing import MongoTestCase
from eduiddashboard import main as eduiddashboard_main
from eduiddashboard import AVAILABLE_LOA_LEVEL
from eduiddashboard.msgrelay import MsgRelay

from eduid_am.celery import celery, get_attribute_manager

import logging
logger = logging.getLogger(__name__)


SETTINGS = {
    'auth_tk_secret': '123456',
    'auth_shared_secret': '123_456',
    'site.name': 'eduiID Testing',
    'saml2.settings_module': path.join(path.dirname(__file__),
                                       'saml2/tests/data/saml2_settings.py'),
    'saml2.login_redirect_url': '/',
    'saml2.logout_redirect_url': '/',
    'saml2.user_main_attribute': 'mail',
    # Required only if not dont want mongodb
    # 'groups_callback': dummy_groups_callback,
    #'session.type': 'memory',
    #'session.lock_dir': '/tmp',
    #'session.webtest_varname': 'session',
    # 'session.secret': '1234',
    'testing': True,
    'jinja2.directories': [
        'eduiddashboard:saml2/templates',
        'eduiddashboard:/templates'
    ],
    'jinja2.undefined': 'strict',
    'jinja2.filters': """
            route_url = pyramid_jinja2.filters:route_url_filter
            static_url = pyramid_jinja2.filters:static_url_filter
            get_flash_message_text = eduiddashboard.filters:get_flash_message_text
            get_flash_message_type = eduiddashboard.filters:get_flash_message_type
            address_type_text = eduiddashboard.filters:address_type_text
            country_name = eduiddashboard.filters:country_name
            context_route_url = eduiddashboard.filters:context_route_url
            safe_context_route_url = eduiddashboard.filters:safe_context_route_url
            """,
    'personal_dashboard_base_url': 'http://localhost/',
    'signup_base_url': 'http://localhost/',
    'nin_service_name': 'Mina meddelanden',
    'nin_service_url': 'http://minameddelanden.se/',
    'mobile_service_name': 'TeleAdress',
    'available_languages': '''
            en = English
            sv = Svenska
            ''',
    'default_country_code': '+46',
    'vccs_url': 'http://localhost:8550/',
    'password_reset_timeout': '120',
    'dashboard_hostname': 'dashboard.example.com',
    'dashboard_baseurl': 'http://dashboard.example.com',
    }


INITIAL_VERIFICATIONS = [{
    '_id': ObjectId('234567890123456789012301'),
    'code': '9d392c',
    'model_name': 'mobile',
    'obj_id': '+34 6096096096',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.datetime.utcnow(),
    'verified': False,
}, {
    '_id': ObjectId(),
    'code': '123123',
    'model_name': 'norEduPersonNIN',
    'obj_id': '210987654321',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.datetime.utcnow(),
    'verified': False,
}, {
    '_id': ObjectId(),
    'code': '123124',
    'model_name': 'norEduPersonNIN',
    'obj_id': '197801011234',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.datetime.utcnow(),
    'verified': True,
}, {
    '_id': ObjectId(),
    'code': '123124',
    'model_name': 'norEduPersonNIN',
    'obj_id': '123456789050',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.datetime.utcnow(),
    'verified': False,
}]


def loa(index):                                                                                                                                             
    return AVAILABLE_LOA_LEVEL[index-1]


class MockedResult(object):

    def __init__(self, retval, failed):
        self.retval = retval
        self.failed = failed
        if not self.failed:
            self.status = 'SUCCESS'
        else:
            self.status = 'FAILED'

    def get(self):
        if not self.failed:
            return self.retval
        else:
            raise MsgRelay.TaskFailed('task failed')

    def wait(self):
        if not self.failed:
            return self.retval
        else:
            raise MsgRelay.TaskFailed('task failed')

    def successful(self):
        return self.status == 'SUCCESS'


class MockedTask(object):

    def __init__(self, *args, **kwargs):
        self.retval = None
        self.failed = False

    def apply(self, *args, **kwargs):
        return MockedResult(self.retval, self.failed)

    def delay(self, *args, **kwargs):
        return MockedResult(self.retval, self.failed)

    def apply_async(self, *args, **kwargs):
        return MockedResult(self.retval, self.failed)


class LoggedInRequestTests(MongoTestCase):
    """Base TestCase for those tests that need a logged in environment setup"""

    def setUp(self, settings={}, skip_on_fail=False, std_user='johnsmith@example.com'):

        self.settings = deepcopy(SETTINGS)
        self.settings.update(settings)
        super(LoggedInRequestTests, self).setUp(celery, get_attribute_manager, userdb_use_old_format=True)

        self.settings['mongo_uri'] = self.mongodb_uri('')
        try:
            app = eduiddashboard_main({}, **self.settings)
        except pymongo.errors.ConnectionFailure:
            if skip_on_fail:
                raise unittest.SkipTest("requires accessible MongoDB server on {!r}".format(
                    self.settings['mongo_uri']))
            raise

        self.testapp = TestApp(app)

        self.config = testing.setUp()
        self.config.registry.settings = self.settings
        self.config.registry.registerUtility(self, IDebugLogger)

        self.userdb = app.registry.settings['userdb']
        _userdoc = self.userdb.get_user_by_mail(std_user)
        self.assertIsNotNone(_userdoc, "Could not load the standard test user {!r} from the database {!s}".format(
            std_user, self.userdb))
        self.user = OldUser(data=_userdoc)

        #self.db = get_db(self.settings)
        self.db = app.registry.settings['mongodb'].get_database('eduid_dashboard')    # central userdb, raw mongodb
        self.userdb_new = UserDB(self.mongodb_uri(''), 'eduid_userdb')   # central userdb in new format (User)
        self.dashboard_db = DashboardUserDB(self.mongodb_uri('eduid_dashboard'))
        # Clean up the dashboards private database collections
        logger.debug("Dropping profiles, verifications and reset_passwords from {!s}".format(self.db))
        self.db.profiles.drop()
        self.db.verifications.drop()
        self.db.reset_passwords.drop()

        # Copy all the users from the eduid userdb into the dashboard applications userdb
        # since otherwise the out-of-sync check will trigger on every save to the dashboard
        # applications database because there is no document there with the right modified_ts
        for userdoc in self.userdb._get_all_docs():
            logger.debug("COPYING USER INTO PROFILES:\n{!s}".format(userdoc))
            self.db.profiles.insert(userdoc)

        self.initial_verifications = (getattr(self, 'initial_verifications', None)
                                      or INITIAL_VERIFICATIONS)

        for verification_data in self.initial_verifications:
            self.db.verifications.insert(verification_data)

    def tearDown(self):
        super(LoggedInRequestTests, self).tearDown()
        logger.debug("tearDown: Dropping profiles, verifications and reset_passwords from {!s}".format(self.db))
        for userdoc in self.db.profiles.find({}):
            assert OldUser(userdoc)
        self.db.profiles.drop()
        self.db.verifications.drop()
        self.db.reset_passwords.drop()
        self.testapp.reset()

    def dummy_get_user(self, userid=''):
        return self.user

    def set_mocked_get_user(self):
        patcher = patch('eduid_userdb.dashboard.UserDBWrapper.get_user_by_eppn',
                        self.dummy_get_user)
        patcher.start()

    def dummy_request(self, cookies={}):
        request = DummyRequest()
        request.context = DummyResource()
        request.userdb = self.userdb
        request.db = self.db
        request.registry.settings = self.settings
        return request

    def set_logged(self, email='johnsmith@example.com', extra_session_data={}):
        request = self.set_user_cookie(email)
        user_obj = self.userdb.get_user_by_mail(email, raise_on_missing=True)
        if not user_obj:
            logging.error("User {!s} not found in database {!r}. Users:".format(email, self.userdb))
            for this in self.userdb._get_all_userdocs():
                this_user = OldUser(this)
                logging.debug("  User: {!s}".format(this_user))
        # user only exists in eduid-userdb, so need to clear modified-ts to be able
        # to save it to eduid-dashboard.profiles
        user_obj.set_modified_ts(None)
        session_data = {
            'user': user_obj,
            'eduPersonAssurance': loa(3),
            'eduPersonIdentityProofing': loa(3),
        }
        session_data.update(extra_session_data)
        request = self.add_to_session(session_data)
        return request

    def set_user_cookie(self, user_id):
        request = TestRequest.blank('', {})
        request.registry = self.testapp.app.registry
        remember_headers = remember(request, user_id)
        cookie_value = remember_headers[0][1].split('"')[1]
        self.testapp.set_cookie('auth_tkt', cookie_value)
        return request

    def add_to_session(self, data):
        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)
        request = self.dummy_request()
        session = session_factory(request)
        for key, value in data.items():
            session[key] = value
        session.persist()
        self.testapp.set_cookie(session_factory._options.get('key'), session._sess.id)
        return request

    def check_values(self, fields, values, ignore_not_found=[]):
        for field in fields:
            if field.attrs['type'] == 'checkbox':
                # A webtest.app.Checkbox only has a value if it is checked (!)
                old_status = field.checked
                field.checked = True
                if field.value in values:
                    logger.debug("Checked checkbox {!r} (value {!r})".format(field.id, field.value))
                    values.remove(field.value)
                else:
                    # restore the checkbox whose value was not found in values
                    field.checked = old_status
        values = [x for x in values if x not in ignore_not_found]
        self.assertEqual(values, [], "Failed checking one or more checkboxes: {!r}".format(values))


    def values_are_checked(self, fields, values):
        checked = [f.value for f in fields if f.value is not None]

        self.assertEqual(values, checked)
