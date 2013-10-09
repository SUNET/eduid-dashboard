from eduiddashboard.saml2.testing import Saml2RequestTests

from eduiddashboard.saml2.auth import get_loa, authenticate, login

from eduiddashboard import AVAILABLE_LOA_LEVEL


class AuthTests(Saml2RequestTests):

    def test_get_loa(self):
        self.assertEqual(
            get_loa(
                AVAILABLE_LOA_LEVEL,
                {'ava': {'eduPersonAssurance': ['http://www.swamid.se/assurance/al1']}}
            ),
            'http://www.swamid.se/assurance/al1'
        )
        self.assertEqual(
            get_loa(AVAILABLE_LOA_LEVEL, None),
            'http://www.swamid.se/assurance/al1'
        )
        self.assertEqual(
            get_loa(AVAILABLE_LOA_LEVEL,
                    {'ava': {'eduPersonAssurance': ['http://www.swamid.se/assurance/al2']}}),
            'http://www.swamid.se/assurance/al2'
        )
        self.assertEqual(
            get_loa(AVAILABLE_LOA_LEVEL,
                    {'ava': {'eduPersonAssurance': 'potatoes'}}),
            'http://www.swamid.se/assurance/al1'
        )
        self.assertEqual(
            get_loa(AVAILABLE_LOA_LEVEL,
                    {'ava': {'nokey': 'potatoes'}}),
            'http://www.swamid.se/assurance/al1'
        )

    def test_authenticate(self):
        request = self.dummy_request()

        attribute_mapping = {
            'mail': 'mail',
        }
        session_info = self.get_fake_session_info()

        user = authenticate(request, session_info, attribute_mapping)

        # The user provide exists
        self.assertEqual([user['mail']], session_info['ava']['mail'])

        user = authenticate(request,
                            self.get_fake_session_info('notexists@example.com'),
                            attribute_mapping)
        # The user does not exist
        self.assertIsNone(user)

        user = authenticate(request,
                            self.get_fake_session_info('notexists@example.com'),
                            {'NOTmail': 'mail'})
        # The main_attribute not in attribute_mapping or ava
        self.assertIsNone(user)

    def test_login(self):
        session_info = self.get_fake_session_info()
        request = self.get_request_with_session()

        attribute_mapping = {
            'mail': 'mail',
        }

        user = authenticate(request, session_info, attribute_mapping)

        headers = login(request, session_info, user)
        self.assertEqual(headers, True)
        self.assertNotEqual(headers, [])
