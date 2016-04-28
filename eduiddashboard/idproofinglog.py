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

    def __init__(self, user):
        self._required_keys = ['created', 'eppn']
        self.data = dict()
        self.data['created'] = datetime.utcnow()
        self.data['eppn'] = user.eppn

    def validate(self, d):
        # Check that all keys are accounted for and that none of them evaluates to false
        if not all(d.get(key) for key in self._required_keys):
            logger.error('Not enough data to log proofing event: {!r}. Required keys: {!r}'.format(
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
            'eppn': eppn,
            'created': datetime.utcnow()
            'reason': 'matched',
            'nin': national_identity_number,
            'mobile_number': mobile_number,
            'teleadress_response': {teleadress_response},
            'user_postal_address': {postal_address_from_navet}
        }
    """

    def __init__(self, user, reason, nin, mobile_number, user_postal_address):
        """
        :param user: user object
        :type user: User
        :param reason: Reason for mobile phone number match to user
        :type reason: str
        :param nin: National identity number
        :type nin: str
        :param mobile_number: Mobile phone number
        :type mobile_number: str
        :param user_postal_address: Navet response for users official address
        :type user_postal_address: dict
        :return: TeleAdressProofing object
        :rtype: TeleAdressProofing
        """
        super(TeleAdressProofing, self).__init__(user)
        self._required_keys.extend(['proofing_method', 'reason', 'nin', 'mobile_number', 'user_postal_address'])
        self.data['proofing_method'] = 'TeleAdress'
        self.data['reason'] = reason
        self.data['nin'] = nin
        self.data['mobile_number'] = mobile_number
        self.data['user_postal_address'] = user_postal_address


class TeleAdressProofingRelation(TeleAdressProofing):
    """
    data = {
            'eppn': eppn,
            'created': datetime.utcnow()
            'reason': 'match_by_navet',
            'nin': national_identity_number,
            'mobile_number': mobile_number,
            'teleadress_response': {teleadress_response},
            'user_postal_address': {postal_address_from_navet}
            'mobile_number_registered_to': 'registered_national_identity_number',
            'registered_relation': 'registered_relation_to_user'
            'registered_postal_address': {postal_address_from_navet}
        }
    """
    def __init__(self, user, reason, nin, mobile_number, user_postal_address, mobile_number_registered_to,
                 registered_relation, registered_postal_address):
        """
        :param user: user object
        :type user: User
        :param reason: Reason for mobile phone number match to user
        :type reason: str
        :param nin: National identity number
        :type nin: str
        :param mobile_number: Mobile phone number
        :type mobile_number: str
        :param user_postal_address: Navet response for users official address
        :type user_postal_address: dict
        :param mobile_number_registered_to: NIN of registered user of mobile phone subscription
        :type mobile_number_registered_to: str
        :param registered_relation: Relation of mobile phone subscriber to User
        :type registered_relation: str
        :param registered_postal_address: Navet response for mobile phone subscriber
        :type registered_postal_address:  dict
        :return: TeleAdressProofingRelation object
        :rtype: TeleAdressProofingRelation
        """
        super(TeleAdressProofingRelation, self).__init__(user, reason, nin, mobile_number, user_postal_address)
        self._required_keys.extend(['mobile_number_registered_to', 'registered_relation', 'registered_postal_address'])
        self.data['mobile_number_registered_to'] = mobile_number_registered_to
        self.data['registered_relation'] = registered_relation
        self.data['registered_postal_address'] = registered_postal_address


class LetterProofing(IDProofingData):
    """
    data = {
            'eppn': eppn,
            'created': datetime.utcnow()
            'nin': 'national_identity_number',
            'letter_sent_to': {address_letter_was_sent_to},
            'transaction_id': 'transaction_id',
            'user_postal_address': {postal_address_from_navet}
        }
    """

    def __init__(self, user, nin, letter_sent_to, transaction_id, user_postal_address):
        """
        :param user: user object
        :type user: User
        :param nin: National identity number
        :type nin: str
        :param letter_sent_to: Name and address the letter was sent to
        :type letter_sent_to: dict
        :param transaction_id: Letter service transaction id
        :type transaction_id: str
        :param user_postal_address: Navet response for users official address
        :type user_postal_address: dict
        :return: LetterProofing object
        :rtype: LetterProofing
        """
        super(LetterProofing, self).__init__(user)
        self._required_keys.extend(['proofing_method', 'nin', 'letter_sent_to', 'transaction_id',
                                    'user_postal_address'])
        self.data['proofing_method'] = 'eduid-idproofing-letter'
        self.data['nin'] = nin
        self.data['letter_sent_to'] = letter_sent_to
        self.data['transaction_id'] = transaction_id
        self.data['user_postal_address'] = user_postal_address


class IDProofingLog(object):
    def __init__(self, config):
        self.mongodb_uri = config['mongo_uri']
        self.collection = MongoDB(self.mongodb_uri).get_collection('id_proofing_log', database_name='eduid_dashboard')

    def _insert(self, doc):
        self.collection.insert(doc, safe=True)  # Make sure the write succeeded

    def log_verification(self, id_proofing_data):
        """
        @param id_proofing_data:
        @type id_proofing_data: IDProofingData
        @return: Boolean
        @rtype: bool
        """
        doc = id_proofing_data.to_dict()
        if doc:
            self._insert(doc)
            return True
        return False

