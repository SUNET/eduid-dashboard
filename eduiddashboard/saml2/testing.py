import re
import unittest
from os import path

from webtest import TestApp, TestRequest

from pyramid.config import Configurator
from pyramid.interfaces import ISessionFactory
from pyramid.security import (remember, Allow, Authenticated, Everyone,
                              ALL_PERMISSIONS)
from pyramid.testing import DummyRequest

from eduiddashboard.saml2.userdb import IUserDB
from eduiddashboard.saml2 import includeme as saml2_includeme
from eduiddashboard.saml2 import configure_authtk


class MockedUserDB(IUserDB):

    test_users = {
        'user1@example.com': {
            'email': 'user1@example.com',
            'first_name': 'User',
            'last_name': '1',
            'screen_name': 'user1',
        },
        'user2@example.com': {
            'email': 'user2@example.com',
            'first_name': 'User',
            'last_name': '2',
            'screen_name': 'user2',
        },
    }

    def __init__(self):
        pass

    def get_user(self, userid):
        if userid not in self.test_users:
            raise self.UserDoesNotExist
        return self.test_users.get(userid)


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
        pass


def saml2_main(global_config, **settings):
    """ This function returns a WSGI application.

        This is only useful for testing

    """
    settings = dict(settings)

    config = Configurator(settings=settings,
                          root_factory=RootFactory)

    config = configure_authtk(config, settings)

    config.include('pyramid_beaker')
    config.include('pyramid_jinja2')

    saml2_includeme(config)

    config.scan(ignore=[re.compile('.*tests.*').search, '.testing'])
    return config.make_wsgi_app()


class Saml2RequestTests(unittest.TestCase):
    """Base TestCase for those tests that need a full environment setup"""

    def setUp(self):
        # Don't call DBTests.setUp because we are getting the
        # db in a different way
        self.settings = {
            'auth_tk_secret': '123456',
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'tests/data/saml2_settings.py'),
            'saml2.login_redirect_url': '/',
            'saml2.user_main_attribute': 'email',
            'saml2.attribute_mapping': "email = mail",
            'auth_tk_secret': '123456',
            'testing': True,
            'jinja2.directories': 'eduiddashboard:saml2/templates',
            'jinja2.undefined': 'strict',
            'jinja2.filters': """
                route_url = pyramid_jinja2.filters:route_url_filter
                static_url = pyramid_jinja2.filters:static_url_filter
            """,
        }
        app = saml2_main({}, **self.settings)
        self.testapp = TestApp(app)

    def tearDown(self):
        super(Saml2RequestTests, self).tearDown()
        self.testapp.reset()

    def set_user_cookie(self, user_id):
        request = TestRequest.blank('', {})
        request.registry = self.testapp.app.registry
        remember_headers = remember(request, user_id)
        cookie_value = remember_headers[0][1].split('"')[1]
        self.testapp.cookies['auth_tkt'] = cookie_value

    def add_to_session(self, data):
        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)
        request = DummyRequest()
        session = session_factory(request)
        for key, value in data.items():
            session[key] = value
        session.persist()
        self.testapp.cookies['beaker.session.id'] = session._sess.id
        return request

    def dummy_request(self):
        request = DummyRequest()
        request.userdb = MockedUserDB()
        return request
