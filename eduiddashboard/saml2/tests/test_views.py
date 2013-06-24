from os import path

from eduiddashboard.saml2.testing import Saml2RequestTests


class Saml2ViewsTests(Saml2RequestTests):

    def test_forbidden_view_nologgedin(self):
        # If user is not logged, return forbidden
        res = self.testapp.get('/saml2/forbidden/')
        self.assertEqual(res.status, '302 Found')

    def test_forbidden_view_loggedin(self):
        self.config.testing_securitypolicy(userid='user', permissive=True)

        self.set_user_cookie('user')

        res = self.testapp.get('/saml2/forbidden/')
        self.assertEqual(res.status, '302 Found')
        self.assertEqual('http://localhost/', res.location)

    def test_login_nologgedin(self):
        res = self.testapp.get('/saml2/login/')
        self.assertEqual(res.status, '302 Found')
        self.assertIn('https://idp.example.com/simplesaml/saml2/idp/SSOService'
                      '.php?SAMLRequest=', res.location)

    def test_login_loggedin(self):
        self.config.testing_securitypolicy(userid='user', permissive=True)

        self.set_user_cookie('user')

        res = self.testapp.get('/saml2/login/?next=/afterlogin/')
        self.assertEqual(res.status, '302 Found')
        self.assertIn('/afterlogin/', res.location)


class Saml2ViewsTestsUsingWayf(Saml2RequestTests):

    def setUp(self):
        super(Saml2ViewsTestsUsingWayf, self).setUp({
            'saml2.settings_module': path.join(path.dirname(__file__),
                                               'data/saml2_settings_wayf.py'),
        })

    def test_login_nologgedin(self):
        res = self.testapp.get('/saml2/login/')
        self.assertEqual(res.status_code, 200)
