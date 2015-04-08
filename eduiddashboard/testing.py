from os import path
import datetime
from copy import deepcopy

from mock import patch
import pymongo

import unittest

from webtest import TestApp, TestRequest

from pyramid.interfaces import ISessionFactory, IDebugLogger
from pyramid.security import remember
from pyramid.testing import DummyRequest, DummyResource
from pyramid import testing

from eduid_userdb.db import MongoDB
from eduiddashboard.user import DashboardLegacyUser as OldUser
from eduid_userdb.testing import MongoTestCase
from eduiddashboard import main as eduiddashboard_main
from eduiddashboard import AVAILABLE_LOA_LEVEL
from eduiddashboard.msgrelay import MsgRelay

from eduid_am.celery import celery, get_attribute_manager

MONGO_URI_TEST = 'mongodb://localhost:27017/eduid_signup_test'
MONGO_URI_TEST_AM = 'mongodb://localhost:27017/eduid_am_test'
MONGO_URI_TEST_TOU = 'mongodb://localhost:27017/eduid_tou_test'
MONGO_URI_AUTHNINFO_TEST = 'mongodb://localhost:27017/eduid_idp_authninfo_test'


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
    #'mongo_uri': MONGO_URI_TEST,
    #'mongo_uri_am': MONGO_URI_TEST_AM,
    #'mongo_uri_authninfo': MONGO_URI_AUTHNINFO_TEST,
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
    'nin_service_name': 'Mina meddelanden',
    'nin_service_url': 'http://minameddelanden.se/',
    'available_languages': '''
            en = English
            sv = Svenska
            ''',
    'default_country_code': '+46',
    'vccs_url': 'http://localhost:8550/',
    'password_reset_timeout': '120',
    }


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


def get_db(settings):
    mongo_replicaset = settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        mongodb = MongoDB(db_uri=settings['mongo_uri'],
                          replicaSet=mongo_replicaset)
    else:
        mongodb = MongoDB(db_uri=settings['mongo_uri'])
    return mongodb.get_database()


class LoggedInRequestTests(MongoTestCase):
    """Base TestCase for those tests that need a logged in environment setup"""

    #MockedUserDB = am.MockedUserDB

    #user = User(data=am.MOCKED_USER_STANDARD)
    #user.modified_ts = True
    #users = []

    def setUp(self, settings={}):
        super(LoggedInRequestTests, self).setUp(celery, get_attribute_manager)

        #if getattr(self, 'settings', None) is None:
        self.settings = SETTINGS
        self.settings.update(settings)

        mongo_settings = {
            'mongo_uri': self.mongodb_uri('eduid_dashboard'),
            'mongo_uri_am': self.mongodb_uri('eduid_userdb'),
            'mongo_uri_authninfo': self.mongodb_uri('authninfo'),
        }

        self.settings.update(mongo_settings)

        try:
            app = eduiddashboard_main({}, **self.settings)
        except pymongo.errors.ConnectionFailure:
            raise unittest.SkipTest("requires accessible MongoDB server on {!r}".format(
                self.settings['mongo_uri']))

        self.testapp = TestApp(app)

        self.config = testing.setUp()
        self.config.registry.settings = self.settings
        self.config.registry.registerUtility(self, IDebugLogger)

        self.userdb = app.registry.settings['userdb']

        #self.db = get_db(self.settings)
        self.db = app.registry.settings['mongodb'].get_database()
        self.db.profiles.drop()
        self.db.verifications.drop()
        for verification_data in self.initial_verifications:
            self.db.verifications.insert(verification_data)

        #userdocs = []
        ##ts = datetime.datetime.utcnow()
        #for userdoc in self.userdb.all_userdocs():
        #    newdoc = deepcopy(userdoc)
        ##    newdoc['modified_ts'] = ts
        #    userdocs.append(newdoc)
        #self.db.profiles.insert(userdocs)


    def tearDown(self):
        super(LoggedInRequestTests, self).tearDown()
        self.db.profiles.drop()
        self.db.verifications.drop()
        self.db.reset_passwords.drop()
        self.testapp.reset()

    def dummy_get_user(self, userid=''):
        return self.user

    def set_mocked_get_user(self):
        patcher = patch('eduid_am.userdb.UserDB.get_user',
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
        user_obj = self.userdb.get_user_by_mail(email)
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
        self.testapp.cookies['auth_tkt'] = cookie_value
        return request

    def add_to_session(self, data):
        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)
        request = self.dummy_request()
        session = session_factory(request)
        for key, value in data.items():
            session[key] = value
        session.persist()
        self.testapp.cookies[session_factory._options.get('key')] = session._sess.id
        return request

    def check_values(self, fields, values):
        for field in fields:
            if field.attrs['type'] == 'checkbox':
                old_status = field.checked
                field.checked = True
                if field.value not in values:
                    field.checked = old_status

    def values_are_checked(self, fields, values):
        checked = [f.value for f in fields if f.value is not None]

        self.assertEqual(values, checked)
