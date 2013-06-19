import unittest

from eduiddashboard.saml2.cache import (pyramidSessionCacheAdapter,
                                        OutstandingQueriesCache,
                                        IdentityCache, StateCache)


class pyramidSessionCacheAdapterTests(unittest.TestCase):

    def test_init(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        psca = pyramidSessionCacheAdapter(fake_session_dict, 'saml2')

        self.assertEqual(psca.session, fake_session_dict)
        self.assertEqual(psca.key, psca.key_prefix + 'saml2')

    def test_get_objects(self):
        pass

    def test_set_objects(self):
        pass

    def test_sync(self):
        pass
