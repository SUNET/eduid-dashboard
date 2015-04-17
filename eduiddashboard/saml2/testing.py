import re
from copy import deepcopy
from datetime import datetime
import unittest
from os import path

import pymongo
from webtest import TestApp, TestRequest

from pyramid.config import Configurator

from pyramid.interfaces import ISessionFactory, IDebugLogger
from pyramid.security import (remember, Allow, Authenticated, Everyone,
                              ALL_PERMISSIONS)
from pyramid.testing import DummyRequest, DummyResource
from pyramid import testing

from eduid_userdb.userdb import UserDB
import eduid_userdb.exceptions
from eduid_userdb.dashboard import DashboardLegacyUser as OldUser
from eduiddashboard.saml2 import includeme as saml2_includeme
from eduid_userdb.testing import MongoTemporaryInstance


class MockedUserDB(UserDB):

    test_users = {
        'user1@example.com': {
            '_id': 1,
            'mail': 'user1@example.com',
            'first_name': 'User',
            'last_name': '1',
            'screen_name': 'user1',
            'modified_ts': datetime.utcnow(),
        },
        'user2@example.com': {
            '_id': 2,
            'mail': 'user2@example.com',
            'first_name': 'User',
            'last_name': '2',
            'screen_name': 'user2',
            'modified_ts': datetime.utcnow(),
        },
    }

    def __init__(self):
        self.exceptions = eduid_userdb.exceptions

    def get_user(self, userid):
        if userid not in self.test_users:
            raise self.exceptions.UserDoesNotExist
        return OldUser(self.test_users.get(userid))
    
    def all_users(self):
        for user in self.test_users.values():
            yield OldUser(deepcopy(user))

    def all_userdocs(self):
        for user in self.test_users.values():
            yield deepcopy(user)


class RootFactory(object):
    __acl__ = [
        (Allow, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class ObjectFactory(object):
    __acl__ = [
        (Allow, Authenticated, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


def saml2_main(global_config, **settings):
    """ This function returns a WSGI application.

        This is only useful for saml2 testing

    """
    settings = dict(settings)

    config = Configurator(settings=settings,
                          root_factory=RootFactory)

    config.include('pyramid_beaker')
    config.include('pyramid_jinja2')
    config.set_request_property(lambda x: get_db(settings), 'db', reify=True)

    saml2_includeme(config)

    config.scan(ignore=[re.compile('.*tests.*').search, '.testing'])
    return config.make_wsgi_app()


def dummy_groups_callback(userid, request):
    return ['']


class Saml2RequestTests(unittest.TestCase):
    """Base TestCase for those tests usign saml2 that need a full environment
       setup
    """

    def setUp(self, settings={}):
        # Don't call DBTests.setUp because we are getting the
        # db in a different way

        self.tmp_db = MongoTemporaryInstance.get_instance()

        self.settings = {
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'tests/data/saml2_settings.py'),
            'saml2.login_redirect_url': '/',
            'saml2.logout_redirect_url': '/',
            'saml2.user_main_attribute': 'mail',
            'auth_tk_secret': '123456',
            'mongo_uri': self.tmp_db.get_uri('eduid_dashboard_test'),
            'testing': True,
            'jinja2.directories': 'eduiddashboard:saml2/templates',
            'jinja2.undefined': 'strict',
            'jinja2.filters': """
                route_url = pyramid_jinja2.filters:route_url_filter
                static_url = pyramid_jinja2.filters:static_url_filter
            """,
        }
        self.settings.update(settings)

        if not self.settings.get('groups_callback', None):
            self.settings['groups_callback'] = dummy_groups_callback

        app = saml2_main({}, **self.settings)
        self.testapp = TestApp(app)
        self.userdb = MockedUserDB()
        try:
            self.db = self.tmp_db.conn['eduid_dashboard_test']
        except pymongo.errors.ConnectionFailure:
            raise unittest.SkipTest("requires accessible MongoDB server on {!r}".format(
                self.settings['mongo_uri']))
        self.db.profiles.drop()
        userdocs = []
        for userdoc in self.userdb.all_userdocs():
            newdoc = deepcopy(userdoc)
            userdocs.append(newdoc)
        self.db.profiles.insert(userdocs)

        self.config = testing.setUp()
        self.config.registry.settings = self.settings
        self.config.registry.registerUtility(self, IDebugLogger)

    def tearDown(self):
        super(Saml2RequestTests, self).tearDown()
        self.testapp.reset()
        self.db.profiles.drop()

    def set_user_cookie(self, user_id):
        request = TestRequest.blank('', {})
        request.userdb = self.userdb
        request.db = self.db
        request.registry = self.testapp.app.registry
        remember_headers = remember(request, user_id)
        cookie_value = remember_headers[0][1].split('"')[1]
        self.testapp.cookies['auth_tkt'] = cookie_value
        return request

    def dummy_request(self):
        request = DummyRequest()
        request.context = DummyResource()
        request.userdb = self.userdb
        request.db = self.db
        request.registry.settings = self.settings
        return request

    def get_request_with_session(self):
        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)

        request = self.dummy_request()
        session = session_factory(request)
        session.persist()
        self.testapp.cookies['beaker.session.id'] = session._sess.id
        self.pol = self.config.testing_securitypolicy(
            'user', ('editors', ),
            permissive=False, remember_result=True)
        return request

    def get_fake_session_info(self, user=None):
        session_info = {
            'authn_info': [
                ('urn:oasis:names:tc:SAML:2.0:ac:classes:Password', [])
            ],
            'name_id': None,
            'not_on_or_after': 1371671386,
            'came_from': u'/',
            'ava': {
                'cn': ['Usuario1'],
                'objectclass': ['top', 'inetOrgPerson', 'person', 'eduPerson'],
                'userpassword': ['1234'],
                'edupersonaffiliation': ['student'],
                'sn': ['last name'],
                'mail': ['user1@example.com']
            },
            'issuer': 'https://idp.example.com/saml/saml2/idp/metadata.php'
        }

        if user is not None:
            session_info['ava']['mail'] = user

        return session_info
