from eduiddashboard.saml2.testing import Saml2RequestTests

from eduiddashboard.saml2.auth import get_loa, authenticate, login


class AuthTests(Saml2RequestTests):

    def test_get_loa(self):
        self.assertEqual(get_loa({}), 5)
        self.assertEqual(get_loa(None), 5)
        self.assertEqual(get_loa({'LoA': 3}), 3)

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

    def test_authenticate(self):
        request = self.dummy_request()
        request.registry.settings = self.settings

        attribute_mapping = {
            'mail': 'email',
        }
        session_info = self.get_fake_session_info()
        user = authenticate(request, session_info, attribute_mapping)

        # The user provide exists
        self.assertEqual([user['email']], session_info['ava']['mail'])

        # The user does not exist
        self.assertIsNone(authenticate(request,
                          self.get_fake_session_info('notexists@example.com'),
                          attribute_mapping))

        # The main_attribute not in attribute_mapping or ava
        self.assertIsNone(authenticate(request,
                          self.get_fake_session_info('notexists@example.com'),
                          {
                              'NOTmail': 'mail',
                          }))
