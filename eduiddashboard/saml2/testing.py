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

from eduid_userdb.userdb import MongoDB
from eduid_userdb.dashboard import UserDBWrapper
from eduid_userdb.testing import MongoTestCase
from eduiddashboard.saml2 import includeme as saml2_includeme
from eduid_am.celery import celery, get_attribute_manager

import logging
logger = logging.getLogger(__name__)


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


def get_db(settings):
    mongo_replicaset = settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        mongodb = MongoDB(db_uri=settings['mongo_uri'],
                          replicaSet=mongo_replicaset)
    else:
        mongodb = MongoDB(db_uri=settings['mongo_uri'])
    logger.warning("Using a raw MongoDB instance: {!r} (mongo_uri: {!r})".format(mongodb, settings['mongo_uri']))
    return mongodb.get_database()


def saml2_main(global_config, **settings):
    """ This function returns a WSGI application.

        This is only useful for saml2 testing

    """
    settings = dict(settings)

    config = Configurator(settings=settings,
                          root_factory=RootFactory)

    config.include('pyramid_beaker')
    config.include('pyramid_jinja2')
    _userdb = UserDBWrapper(config.registry.settings['mongo_uri_am'])
    config.registry.settings['userdb'] = _userdb
    config.add_request_method(lambda x: x.registry.settings['userdb'], 'userdb', reify=True)
    mongodb = MongoDB(db_uri=settings['mongo_uri'])
    authninfodb = MongoDB(db_uri=settings['mongo_uri_authninfo'])
    config.registry.settings['mongodb'] = mongodb
    config.registry.settings['authninfodb'] = authninfodb
    config.registry.settings['db_conn'] = mongodb.get_connection
    config.registry.settings['db'] = mongodb.get_database()
    config.set_request_property(lambda x: x.registry.settings['mongodb'].get_database(), 'db', reify=True)

    saml2_includeme(config)

    config.scan(ignore=[re.compile('.*tests.*').search, '.testing'])
    return config.make_wsgi_app()


def dummy_groups_callback(userid, request):
    return ['']


class Saml2RequestTests(MongoTestCase):
    """Base TestCase for those tests usign saml2 that need a full environment
       setup
    """

    def setUp(self, settings={}):
        super(Saml2RequestTests, self).setUp(celery, get_attribute_manager, userdb_use_old_format=True)

        self.settings = {
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'tests/data/saml2_settings.py'),
            'saml2.login_redirect_url': '/',
            'saml2.logout_redirect_url': '/',
            'saml2.strip_saml_user_suffix': '@test',
            'auth_tk_secret': '123456',
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

        mongo_settings = {
            'mongo_uri': self.mongodb_uri('eduid_dashboard'),
            'mongo_uri_am': self.mongodb_uri('eduid_userdb'),
            'mongo_uri_authninfo': self.mongodb_uri('authninfo'),
        }
        self.settings.update(mongo_settings)

        app = saml2_main({}, **self.settings)
        self.testapp = TestApp(app)

        self.config = testing.setUp()
        self.config.registry.settings = self.settings
        self.config.registry.registerUtility(self, IDebugLogger)
        self.userdb = app.registry.settings['userdb']
        self.db = app.registry.settings['db']

    def tearDown(self):
        super(Saml2RequestTests, self).tearDown()
        self.testapp.reset()

    def set_user_cookie(self, user_id):
        request = TestRequest.blank('', {})
        request.userdb = self.userdb
        request.db = self.db
        request.registry = self.testapp.app.registry
        remember_headers = remember(request, user_id)
        cookie_value = remember_headers[0][1].split('"')[1]
        self.testapp.set_cookie('auth_tkt', cookie_value)
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
        self.testapp.set_cookie('beaker.session.id', session._sess.id)
        self.pol = self.config.testing_securitypolicy(
            'user', ('editors', ),
            permissive=False, remember_result=True)
        return request

    def get_fake_session_info(self, eppn=None):
        session_info = {
            'authn_info': [
                ('urn:oasis:names:tc:SAML:2.0:ac:classes:Password', [])
            ],
            'name_id': None,
            'not_on_or_after': 1371671386,
            'came_from': u'/',
            'ava': {
                'cn': ['John'],
                'objectclass': ['top', 'inetOrgPerson', 'person', 'eduPerson'],
                'userpassword': ['1234'],
                'edupersonaffiliation': ['student'],
                'sn': ['Smith'],
                'mail': ['johnsmith@example.com'],
                'eduPersonPrincipalName': ['hubba-bubba@test']
            },
            'issuer': 'https://idp.example.com/saml/saml2/idp/metadata.php'
        }

        if eppn is not None:
            session_info['ava']['eduPersonPrincipalName'] = eppn

        return session_info
