from os import path
import base64
from saml2.s_utils import deflate_and_base64_encode
from saml2.mdstore import UnknownPrincipal

from pyramid.interfaces import ISessionFactory
from pyramid.testing import DummyRequest

from eduiddashboard.saml2.cache import OutstandingQueriesCache
from eduiddashboard.saml2.testing import Saml2RequestTests
from eduiddashboard.saml2.tests.responses import (auth_response,
                                                  logout_response,
                                                  logout_request)


class Saml2ViewsTests(Saml2RequestTests):

    def test_forbidden_view_nologgedin(self):
        # If user is not logged, return forbidden
        res = self.testapp.get('/saml2/forbidden/')
        self.assertEqual(res.status, '302 Found')

    def test_forbidden_view_loggedin(self):
        self.config.testing_securitypolicy(userid='user', permissive=True)

        self.set_user_cookie('user')

        self.testapp.get('/saml2/forbidden/', expect_errors=True,
                         status='401 Unauthorized')

    def test_login_nologgedin(self):
        res = self.testapp.get('/saml2/login/')
        self.assertEqual(res.status, '302 Found')
        self.assertIn('https://idp.example.com/simplesaml/saml2/idp/SSOService'
                      '.php?SAMLRequest=', res.location)

    def test_login_loggedin(self):
        self.config.testing_securitypolicy(userid='user1@example.com', permissive=True)

        self.set_user_cookie('user1@example.com')

        res = self.testapp.get('/saml2/login/?next=/afterlogin/')
        self.assertEqual(res.status, '302 Found')
        self.assertIn('/afterlogin/', res.location)

    def add_outstanding_query(self, came_from):

        queryUtility = self.testapp.app.registry.queryUtility
        session_factory = queryUtility(ISessionFactory)
        request = DummyRequest()
        session = session_factory(request)
        session.persist()
        # ensure that session id is a NCName valid
        session._sess.id = "a" + session._sess.id

        oq_cache = OutstandingQueriesCache(session)
        oq_cache.set(session._sess.id, came_from)

        session.persist()

        self.testapp.cookies['beaker.session.id'] = session._sess.id

        return session._sess.id

    def test_assertion_consumer_service(self):
        came_from = '/afterlogin/'

        session_id = self.add_outstanding_query(came_from)

        saml_response = auth_response(session_id, "user1@example.com")

        res = self.testapp.post('/saml2/acs/', params={
            'SAMLResponse': base64.b64encode(saml_response),
            'RelayState': came_from,
        })
        self.assertEquals(res.status_code, 302)
        self.assertEquals(res.location, 'http://localhost' + came_from)

    def test_metadataview(self):
        res = self.testapp.get('/saml2/metadata/')
        self.assertEqual(res.status, '200 OK')

    def test_logout_nologgedin(self):
        res = self.testapp.get('/saml2/logout/')
        self.assertEqual(res.status, '302 Found')
        self.assertIn(self.settings['saml2.logout_redirect_url'], res.location)

    def test_logout_loggedin(self):
        came_from = '/afterlogin/'

        session_id = self.add_outstanding_query(came_from)

        saml_response = auth_response(session_id, "user1@example.com")

        res = self.testapp.post('/saml2/acs/', params={
            'SAMLResponse': base64.b64encode(saml_response),
            'RelayState': came_from,
        })
        cookies = res.cookies_set

        res = self.testapp.get('/saml2/logout/',
                               headers={'cookies': cookies['auth_tkt']})

        self.assertEqual(res.status, '302 Found')
        self.assertIn('https://idp.example.com/simplesaml/saml2/idp/'
                      'SingleLogoutService.php', res.location)

    def test_logout_service_startingSP(self):
        self.config.testing_securitypolicy(userid='user1@example.com',
                                           permissive=True)
        self.set_user_cookie('user1@example.com')

        came_from = '/afterlogin/'
        session_id = self.add_outstanding_query(came_from)

        res = self.testapp.get('/saml2/ls/', params={
            'SAMLResponse': deflate_and_base64_encode(
                logout_response(session_id)
            ),
            'RelayState': 'testing-relay-state',
        })

        self.assertEqual(res.status, '302 Found')
        self.assertIn(self.settings['saml2.logout_redirect_url'], res.location)
        # Set a expired cookie (just the logout header)
        self.assertEqual('auth_tkt=""; Path=/; Domain=localhost; Max-Age=0; '
                         'Expires=Wed, 31-Dec-97 23:59:59 GMT',
                         res.headers.get('Set-Cookie'))

    def test_logout_service_startingSP_already_logout(self):

        came_from = '/afterlogin/'
        session_id = self.add_outstanding_query(came_from)

        res = self.testapp.get('/saml2/ls/', params={
            'SAMLResponse': deflate_and_base64_encode(
                logout_response(session_id)
            ),
            'RelayState': 'testing-relay-state',
        })

        self.assertEqual(res.status, '302 Found')
        self.assertIn(self.settings['saml2.logout_redirect_url'], res.location)
        # Set a expired cookie (just the logout header)
        self.assertEqual('auth_tkt=""; Path=/; Domain=localhost; Max-Age=0; '
                         'Expires=Wed, 31-Dec-97 23:59:59 GMT',
                         res.headers.get('Set-Cookie'))

    def test_logout_service_startingIDP(self):
        self.config.testing_securitypolicy(userid='user1@example.com',
                                           permissive=True)
        self.set_user_cookie('user1@example.com')

        came_from = '/afterlogin/'

        session_id = self.add_outstanding_query(came_from)

        saml_response = auth_response(session_id, "user1@example.com")

        # Log in through IDP SAMLResponse
        res = self.testapp.post('/saml2/acs/', params={
            'SAMLResponse': base64.b64encode(saml_response),
            'RelayState': came_from,
        })

        res = self.testapp.get('/saml2/ls/', params={
            'SAMLRequest': deflate_and_base64_encode(
                logout_request(session_id)
            ),
            'RelayState': 'testing-relay-state',
        })

        self.assertEqual(res.status, '302 Found')
        self.assertIn('https://idp.example.com/simplesaml/saml2/idp/'
                      'SingleLogoutService.php?SAMLResponse=', res.location)
        # Set a expired cookie (just the logout header)
        self.assertEqual('auth_tkt=""; Path=/; Domain=localhost; Max-Age=0; '
                         'Expires=Wed, 31-Dec-97 23:59:59 GMT',
                         res.headers.get('Set-Cookie'))


class Saml2ViewsTestsUsingWayf(Saml2RequestTests):

    def setUp(self):
        super(Saml2ViewsTestsUsingWayf, self).setUp({
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'data/saml2_settings_wayf.py'),
        })

    def test_login_nologgedin(self):
        res = self.testapp.get('/saml2/login/')
        self.assertEqual(res.status_code, 200)
