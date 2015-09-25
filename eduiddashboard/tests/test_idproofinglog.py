# -*- coding: utf-8 -*-
__author__ = 'lundberg'


from eduiddashboard.idproofinglog import IDProofingLog, TeleAdressProofing, TeleAdressProofingRelation
from eduiddashboard.testing import LoggedInRequestTests
from copy import deepcopy


class TestIDProofingLog(LoggedInRequestTests):

    def setUp(self):
        super(TestIDProofingLog, self).setUp()
        self.collection = self.conn['eduid_dashboard']['id_proofing_log']

    def test_teleadress_proofing(self):
        user = self.userdb.get_user_by_mail('johnsmith@example.org')
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
        result = self.collection.find({})
        self.assertEquals(result.count(), 1)
        hit = result.next()
        self.assertEquals(hit['eppn'], user.get_eppn())
        self.assertEquals(hit['reason'], 'matched')
        self.assertEquals(hit['proofing_method'], 'TeleAdress')

    def test_teleadress_proofing_relation(self):
        user = self.userdb.get_user_by_mail('johnsmith@example.org')
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

    def test_teleadress_proofing_extend_bug(self):
        user = self.userdb.get_user_by_mail('johnsmith@example.org')
        data_match = {
            'reason': 'matched',
            'nin': 'some_nin',
            'mobile_number': 'some_mobile_number',
            'user_postal_address': {'response_data': {'some': 'data'}}
        }

        data_relation = {
            'reason': 'matched_by_navet',
            'nin': 'some_nin',
            'mobile_number': 'some_mobile_number',
            'user_postal_address': {'response_data': {'some': 'data'}},
            'mobile_number_registered_to': 'registered_national_identity_number',
            'registered_relation': 'registered_relation_to_user',
            'registered_postal_address': {'response_data': {'some': 'data'}},
        }

        # Make a copy of the original required keys
        required_keys1 = deepcopy(TeleAdressProofing(user, **data_match)._required_keys)
        # Extend the required keys
        TeleAdressProofingRelation(user, **data_relation)
        # Make sure the required keys are instantiated as the original keys
        required_keys2 = TeleAdressProofing(user, **data_match)._required_keys
        self.assertEqual(required_keys1, required_keys2)
