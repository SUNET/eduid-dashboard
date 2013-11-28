from os import path
import base64

from pyramid.interfaces import ISessionFactory
from pyramid.testing import DummyRequest

from eduiddashboard.saml2.cache import OutstandingQueriesCache
from eduiddashboard.saml2.testing import Saml2RequestTests, MockedUserDB
from eduiddashboard.saml2.tests.auth_response import auth_response


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

        res = self.testapp.get('/saml2/logout/', headers={'cookies': cookies['auth_tkt']})

        self.assertEqual(res.status, '302 Found')
        self.assertIn('https://idp.example.com/simplesaml/saml2/idp/SingleLogoutService.php', res.location)


class Saml2ViewsTestsUsingWayf(Saml2RequestTests):

    def setUp(self):
        super(Saml2ViewsTestsUsingWayf, self).setUp({
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'data/saml2_settings_wayf.py'),
        })

    def test_login_nologgedin(self):
        res = self.testapp.get('/saml2/login/')
        self.assertEqual(res.status_code, 200)
