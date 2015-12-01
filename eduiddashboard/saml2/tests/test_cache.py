import unittest

from eduid_common.authn.cache import (SessionCacheAdapter,
                                        OutstandingQueriesCache,
                                        IdentityCache, StateCache)


class pyramidSessionCacheAdapterTests(unittest.TestCase):

    def test_init(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        psca = SessionCacheAdapter(fake_session_dict, 'saml2')

        self.assertEqual(psca.session, fake_session_dict)
        self.assertEqual(psca.key, psca.key_prefix + 'saml2')

    def test_get_objects(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        psca = SessionCacheAdapter(fake_session_dict, 'saml2')

        self.assertEqual(psca._get_objects(), {})

    def test_set_objects(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        psca = SessionCacheAdapter(fake_session_dict, 'saml2')

        psca._set_objects({
            'onekey': 'onevalue',
        })

        self.assertEqual(psca._get_objects(), {'onekey': 'onevalue'})

    def test_sync(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        psca = SessionCacheAdapter(fake_session_dict, 'saml2')

        psca.sync()
        self.assertEqual(psca._get_objects(), {})

        psca['onekey'] = 'onevalue'

        psca.sync()
        self.assertEqual(psca._get_objects(), {'onekey': 'onevalue'})


class OutstandingQueriesCacheTests(unittest.TestCase):

    def test_init(self):
        fake_session_dict = {
            'user': 'someone@example.com',
        }
        oqc = OutstandingQueriesCache(fake_session_dict)

        self.assertIsInstance(oqc._db, SessionCacheAdapter)

    def test_outstanding_queries(self):

        oqc = OutstandingQueriesCache({})
        oqc._db['user'] = 'someone@example.com'
        oqc._db.sync()

        self.assertEqual(oqc.outstanding_queries(), {'user':
                                                     'someone@example.com'})

    def test_set(self):
        oqc = OutstandingQueriesCache({})
        oqc.set('session_id', '/next')

        self.assertEqual(oqc.outstanding_queries(), {'session_id': '/next'})

    def test_delete(self):
        oqc = OutstandingQueriesCache({})
        oqc.set('session_id', '/next')
        self.assertEqual(oqc.outstanding_queries(), {'session_id': '/next'})

        oqc.delete('session_id')

        self.assertEqual(oqc.outstanding_queries(), {})


class IdentityCacheTests(unittest.TestCase):

    def test_init(self):
        ic = IdentityCache({})

        self.assertIsInstance(ic._db, SessionCacheAdapter)
        self.assertTrue(ic._sync, True)
