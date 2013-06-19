from eduiddashboard.saml2.testing import Saml2RequestTests

from eduiddashboard.saml2.auth import get_loa, authenticate, login


class AuthTests(Saml2RequestTests):

    def test_get_loa(self):
        self.assertEqual(get_loa({}), 5)
        self.assertEqual(get_loa(None), 5)
        self.assertEqual(get_loa({'LoA': 3}), 3)

