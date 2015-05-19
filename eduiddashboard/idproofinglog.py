# -*- coding: utf-8 -*-
__author__ = 'lundberg'

#
# Helper functions to log identity proofing events.
#

from datetime import datetime
from eduid_userdb.db import MongoDB
import logging
logger = logging.getLogger(__name__)


class IDProofingData(object):
    _required_keys = ['created', 'eppn']

    def __init__(self, user):
        self.data = dict()
        self.data['created'] = datetime.utcnow()
        self.data['eppn'] = user.get_eppn()

    def validate(self, d):
        # Check that all keys are accounted for and that none of them evaluates to false
        if not all(d.get(key) for key in self._required_keys):
            logger.error('Not enough data to log mobile proofing event: {!r}. Required keys: {!r}'.format(
                d, list(set(self._required_keys)-set(d.keys()))))
            return False
        return True

    def to_dict(self):
        if self.validate(self.data):
            return self.data
        return None


class TeleAdressProofing(IDProofingData):
    """
    data = {
            'reason': 'matched|match_by_navet',
            'nin': national_identity_number,
            'mobile_number': mobile_number,
            'teleadress_response': {teleadress_response},
            'user_postal_address': {postal_address_from_navet}
        }
    """

    def __init__(self, user, data):
        super(TeleAdressProofing, self).__init__(user)
        self._required_keys.extend(['proofing_method', 'reason', 'nin', 'mobile_number', 'teleadress_response',
                                    'user_postal_address'])
        self.data['proofing_method'] = 'TeleAdress'
        self.data.update(data)


class TeleAdressProofingRelation(TeleAdressProofing):
    """
    data = {
            'reason': 'matched|match_by_navet',
            'nin': national_identity_number,
            'mobile_number': mobile_number,
            'teleadress_response': {teleadress_response},
            'user_postal_address': {postal_address_from_navet}
            'registered_to': 'registered_national_identity_number',
            'relation': 'registered_relation_to_user'
            'registered_postal_address': {postal_address_from_navet}
        }
    """
    def __init__(self, user, data):
        super(TeleAdressProofingRelation, self).__init__(user, data)
        self._required_keys.extend(['proofing_method', 'reason', 'nin', 'mobile_number', 'teleadress_response',
                                    'user_postal_address', 'mobile_number_registered_to', 'registered_relation',
                                    'registered_postal_address'])
        self.data.update(data)


class IDProofingLog(object):
    def __init__(self, config):
        conf = config.read_configuration()
        default_mongodb_host = 'localhost'
        default_mongodb_port = 27017
        default_mongodb_name = 'eduid_dashboard'
        default_mongodb_uri = 'mongodb://%s:%d/%s' % (default_mongodb_host, default_mongodb_port, default_mongodb_name)
        self.mongodb_uri = conf['MONGO_URI'] if 'MONGO_URI' in conf else default_mongodb_uri
        self.collection = MongoDB(self.mongodb_uri).get_collection['id_proofing_log']
        self.msgrelay = MsgRelay(conf)

    def insert(self, doc):
        self.collection.insert(doc, w=2)  # Make sure we write to two replicas before returning

    def log_verified_by_mobile(self, id_proofing_data):
        """
        @param id_proofing_data:
        @type id_proofing_data: IDProofingData
        @return: Boolean
        @rtype: bool
        """
        doc = id_proofing_data.to_dict()
        if doc:
            self.insert(doc)
            return True
        return False


def get_idproofinglog(request):
    return request.registry.settings['idproofinglogger']
