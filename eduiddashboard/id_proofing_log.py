# -*- coding: utf-8 -*-
__author__ = 'lundberg'

#
# Helper functions to log identity proofing events.
#

from datetime import datetime
from eduid_am.db import MongoDB
from eduiddashboard.msgrelay import get_postal_address
from eduiddashboard import log


class IDProofingLogger(object):
    def __init__(self, config):
        conf = config.read_configuration()
        default_mongodb_host = 'localhost'
        default_mongodb_port = 27017
        default_mongodb_name = 'eduid_dashboard'
        default_mongodb_uri = 'mongodb://%s:%d/%s' % (default_mongodb_host, default_mongodb_port, default_mongodb_name)
        self.mongodb_uri = conf['MONGO_URI'] if 'MONGO_URI' in conf else default_mongodb_uri
        conn = MongoDB(self.mongodb_uri)
        db = conn.get_database()
        self.collection = db['id_proofing_log']

    def insert(self, doc):
        self.collection.insert(doc, w=2)  # Make sure we write to two replicas before returning

    def verified_by_mobile_relation(self, doc, proofing_data):
        registered_to = proofing_data.get('mobile_number_registered_to')
        lookup_result_relations = proofing_data.get('lookup_result_relations')
        if not registered_to:
            log.critical('Missing mobile_number_registered_to for matched_by_navet event.')
            return None
        if not lookup_result_relations:
            log.critical('Missing lookup_result_relations for matched_by_navet event.')
            return None

        doc['mobile_number_registered_to'] = registered_to
        doc['registered_relation'] = lookup_result_relations
        doc['registered_postal_address'] = get_postal_address(registered_to)

        return doc

    def log_verified_by_mobile(self, user, proofing_data):
        """
        Create a log statement that the user have verified their identity using their mobile phone number.

        proofing_data = {
            'nin': national_identity_number,
            'mobile_number': mobile_number,
            'lookup_results': [{'teleadress': {}}, {'navet': {}}],
            'reason': 'matched|match_by_navet', (status)
            'mobile_number_registered_to': relation (if matched_by_navet)
        }
        """
        # Check that all keys are accounted for and that none of them evaluates to false
        required_keys = ['nin', 'mobile_number', 'lookup_result_teleadress', 'reason']
        if not all(proofing_data.get(key) for key in required_keys):
            log.critical('Not enough data to log mobile proofing event: {!r}. Required keys: {!r}'.format(
                proofing_data, required_keys))
            return False

        doc = {
            'created': datetime.utcnow(),
            'eppn': user.get_eppn(),
            'proofing_method': 'teleadress',
            'reason': proofing_data.get('reason'),
            'nin': proofing_data.get('nin'),
            'mobile_number': proofing_data.get('mobile_number'),
            'user_postal_address': get_postal_address(proofing_data.get('nin'))
        }

        if proofing_data.get('reason') == 'matched_by_navet':
            doc = self.verified_by_mobile_relation(doc, proofing_data)

        if doc:
            self.insert(doc)
            return True
        return False
