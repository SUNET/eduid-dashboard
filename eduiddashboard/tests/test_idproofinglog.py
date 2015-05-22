# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from eduid_userdb import MongoDB
from eduid_userdb.testing import MongoTestCase
from eduid_am.testing import MockedUserDB
from eduiddashboard.idproofinglog import IDProofingLog, TeleAdressProofing, TeleAdressProofingRelation

class TestIDProofingLog(MongoTestCase):

    def setUp(self):
        super(TestIDProofingLog, self).setUp()
        self.userdb = MockedUserDB()
        mongo_uri = self.tmp_db.get_uri('eduid_dashboard_test')
        self.settings.update({
            'mongo_uri': mongo_uri,
        })
        self.collection = MongoDB(mongo_uri).get_collection('id_proofing_log')

    def test_teleadress_proofing(self):
        user = self.userdb.get_user('johnsmith@example.org')
        data = {
            'reason': 'matched',
            'nin': 'some_nin',
            'mobile_number': 'some_mobile_number',
            'user_postal_address': {'response_data': {'some': 'data'}}
        }
        proofing_data = TeleAdressProofing(user, **data)
        self.assertDictContainsSubset(data, proofing_data.to_dict())

        idlog = IDProofingLog(self.settings)
        idlog.log_verified_by_mobile(proofing_data)
        result = self.collection.find()
        self.assertEquals(result.count(), 1)
        hit = result.next()
        self.assertEquals(hit['eppn'], user.get_eppn())
        self.assertEquals(hit['reason'], 'matched')
        self.assertEquals(hit['proofing_method'], 'TeleAdress')

    def test_teleadress_proofing_relation(self):
        user = self.userdb.get_user('johnsmith@example.org')
        data = {
            'reason': 'matched_by_navet',
            'nin': 'some_nin',
            'mobile_number': 'some_mobile_number',
            'user_postal_address': {'response_data': {'some': 'data'}},
            'mobile_number_registered_to': 'registered_national_identity_number',
            'registered_relation': 'registered_relation_to_user',
            'registered_postal_address': {'response_data': {'some': 'data'}},
        }
        proofing_data = TeleAdressProofingRelation(user, **data)
        self.assertDictContainsSubset(data, proofing_data.to_dict())

        idlog = IDProofingLog(self.settings)
        idlog.log_verified_by_mobile(proofing_data)
        result = self.collection.find()
        self.assertEquals(result.count(), 1)
        hit = result.next()
        self.assertEquals(hit['eppn'], user.get_eppn())
        self.assertEquals(hit['reason'], 'matched_by_navet')
        self.assertEquals(hit['proofing_method'], 'TeleAdress')
