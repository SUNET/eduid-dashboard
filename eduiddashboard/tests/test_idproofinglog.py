# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from eduid_userdb.testing import MongoTestCase
from eduid_am.testing import MockedUserDB, UserDB
from eduiddashboard.idproofinglog import TeleAdressProofing, TeleAdressProofingRelation

class IDProofingLog(MongoTestCase):

    userdb = MockedUserDB()

    def test_teleadress_proofing(self):
        user = self.userdb.get_user('johnsmith@example.org')
        data = {
            'reason': 'matched',
            'nin': 'some_nin',
            'mobile_number': 'some_mobile_number',
            'teleadress_response': {'response_data': {'some': 'data'}},
            'user_postal_address': {'response_data': {'some': 'data'}}
        }
        proofing_data = TeleAdressProofing(user, data).to_dict()
        self.assertDictContainsSubset(data, proofing_data)

    def test_teleadress_proofing_ralation(self):
        pass
