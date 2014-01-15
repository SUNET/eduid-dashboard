from datetime import datetime
from os import path
from copy import deepcopy

from bson import ObjectId
from mock import patch
import pymongo

import unittest

from webtest import TestApp, TestRequest

from pyramid.interfaces import ISessionFactory, IDebugLogger
from pyramid.security import remember
from pyramid.testing import DummyRequest, DummyResource
from pyramid import testing

from eduiddashboard.db import MongoDB
from eduiddashboard import main as eduiddashboard_main
from eduiddashboard import AVAILABLE_LOA_LEVEL
from eduiddashboard.saml2.userdb import IUserDB


MONGO_URI_TEST = 'mongodb://localhost:27017/eduid_dashboard_test'
MONGO_URI_AM_TEST = 'mongodb://localhost:27017/eduid_am_test'

MOCKED_USER_STANDARD = {
    '_id': ObjectId('012345678901234567890123'),
    'givenName': 'John',
    'sn': 'Smith',
    'displayName': 'John Smith',
    'norEduPersonNIN': ['123456789013'],
    'photo': 'https://pointing.to/your/photo',
    'preferredLanguage': 'en',
    'eduPersonEntitlement': [
        'urn:mace:eduid.se:role:admin',
        'urn:mace:eduid.se:role:student',
    ],
    'maxReachedLoa': 3,
    'mobile': [{
        'mobile': '609609609',
        'verified': True
    }, {
        'mobile': '+34 6096096096',
        'verified': False
    }],
    'mail': 'johnsmith@example.com',
    'mailAliases': [{
        'email': 'johnsmith@example.com',
        'verified': True,
    }, {
        'email': 'johnsmith2@example.com',
        'verified': True,
    }],
    'postalAddress': [{
        'type': 'home',
        'country': 'SE',
        'address': "Long street, 48",
        'postalCode': "123456",
        'locality': "Stockholm",
        'verified': True,
    }, {
        'type': 'work',
        'country': 'ES',
        'address': "Calle Ancha, 49",
        'postalCode': "123456",
        'locality': "Punta Umbria",
        'verified': False,
    }],
}

INITIAL_VERIFICATIONS = [{
    '_id': ObjectId('234567890123456789012301'),
    'code': '9d392c',
    'model_name': 'mobile',
    'obj_id': '+34 6096096096',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.utcnow(),
    'verified': False,
}, {
    '_id': ObjectId(),
    'code': '123123',
    'model_name': 'norEduPersonNIN',
    'obj_id': '210987654321',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.utcnow(),
    'verified': False,
}, {
    '_id': ObjectId(),
    'code': '123124',
    'model_name': 'norEduPersonNIN',
    'obj_id': '123456789013',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.utcnow(),
    'verified': True,
}, {
    '_id': ObjectId(),
    'code': '123124',
    'model_name': 'norEduPersonNIN',
    'obj_id': '123456789050',
    'user_oid': ObjectId("012345678901234567890123"),
    'timestamp': datetime.utcnow(),
    'verified': False,
}]


class MockedUserDB(IUserDB):

    test_users = {
        'johnsmith@example.com': MOCKED_USER_STANDARD,
        'johnsmith@example.org': deepcopy(MOCKED_USER_STANDARD),
    }
    test_users['johnsmith@example.org']['mail'] = 'johnsmith@example.org'
    test_users['johnsmith@example.org']['mailAliases'][0]['email'] = 'johnsmith@example.org'
    test_users['johnsmith@example.org']['mailAliases'][1]['email'] = 'johnsmith2@example.org'
    test_users['johnsmith@example.org']['_id'] = ObjectId('901234567890123456789012')
    test_users['johnsmith@example.org']['norEduPersonNIN'] = []

    def __init__(self, users=[]):
        for user in users:
            if user.get('mail', '') in self.test_users:
                self.test_users[user['mail']].update(user)

    def get_user(self, userid):
        if userid not in self.test_users:
            raise self.UserDoesNotExist
        return deepcopy(self.test_users.get(userid))

    def all_users(self):
        for userid, user in self.test_users.items():
            yield deepcopy(user)


def loa(index):
    return AVAILABLE_LOA_LEVEL[index-1]


def dummy_groups_callback(userid, request):
    return [request.context.workmode]


def get_db(settings):
    mongo_replicaset = settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        mongodb = MongoDB(settings['mongo_uri'],
                          replicaSet=mongo_replicaset)
    else:
        mongodb = MongoDB(settings['mongo_uri'])
    return mongodb.get_database()


class LoggedInReguestTests(unittest.TestCase):
    """Base TestCase for those tests that need a logged in environment setup"""

    MockedUserDB = MockedUserDB

    user = MOCKED_USER_STANDARD
    users = []

    def setUp(self, settings={}):
        # Don't call DBTests.setUp because we are getting the
        # db in a different way

        self.settings = {
            'auth_tk_secret': '123456',
            'auth_shared_secret': '123_456',
            'site.name': 'eduiID Testing',
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'saml2/tests/data/saml2_settings.py'),
            'saml2.login_redirect_url': '/',
            'saml2.logout_redirect_url': '/',
            'saml2.user_main_attribute': 'mail',
            'saml2.attribute_mapping': "mail = mail",
            # Required only if not dont want mongodb
            # 'groups_callback': dummy_groups_callback,
            #'session.type': 'memory',
            #'session.lock_dir': '/tmp',
            #'session.webtest_varname': 'session',
            # 'session.secret': '1234',
            'mongo_uri': MONGO_URI_TEST,
            'mongo_uri_am': MONGO_URI_AM_TEST,
            'testing': True,
            'jinja2.directories': 'eduiddashboard:saml2/templates',
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
            'available_languages': 'en es',
            'default_country_code': '+46',
            'vccs_url': 'http://localhost:8550/',
        }

        self.settings.update(settings)

        try:
            app = eduiddashboard_main({}, **self.settings)
        except pymongo.errors.ConnectionFailure:
            raise unittest.SkipTest("requires accessible MongoDB server on {!r}".format(
                self.settings['mongo_uri']))

        self.testapp = TestApp(app)

        self.config = testing.setUp()
        self.config.registry.settings = self.settings
        self.config.registry.registerUtility(self, IDebugLogger)
        mongo_replicaset = self.settings.get('mongo_replicaset', None)

        self.db = get_db(self.settings)
        self.amdb = get_db({
            'mongo_replicaset': mongo_replicaset,
            'mongo_uri': self.settings.get('mongo_uri_am'),
        })

        self.userdb = self.MockedUserDB(self.users)

        self.db.profiles.drop()
        self.db.verifications.drop()
        self.initial_verifications = (getattr(self, 'initial_verifications', None)
                                      or INITIAL_VERIFICATIONS)
        for verification_data in self.initial_verifications:
            self.db.verifications.insert(verification_data)
        self.amdb.attributes.drop()

        users = []
        for user in self.userdb.all_users():
            users.append(user)

        self.db.profiles.insert(users)
        self.amdb.attributes.insert(users)

    def tearDown(self):
        super(LoggedInReguestTests, self).tearDown()
        self.db.profiles.drop()
        self.db.verifications.drop()
        self.amdb.attributes.drop()
        self.testapp.reset()

    def dummy_get_user(self, userid=''):
        return self.user

    def set_mocked_get_user(self):
        patcher = patch('eduiddashboard.userdb.UserDB.get_user',
                        self.dummy_get_user)
        patcher.start()

    def dummy_request(self, cookies={}):
        request = DummyRequest()
        request.context = DummyResource()
        request.userdb = self.userdb
        request.registry.settings = self.settings
        return request

    def set_logged(self, user='johnsmith@example.com', extra_session_data={}):
        request = self.set_user_cookie(user)
        user_obj = self.userdb.get_user(user)
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
