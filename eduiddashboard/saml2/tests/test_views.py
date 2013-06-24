from eduiddashboard.saml2.testing import Saml2RequestTests



class Saml2ViewsTests(Saml2RequestTests):

    def test_forbidden_view_nologed(self):
        # If user is not logged, return forbidden
        res = self.testapp.get('/saml2/forbidden/')
        self.assertEqual(res.status, '302 Found')
