# -*- coding: utf-8 -*-

import optparse
import sys
import textwrap
from pyramid.paster import bootstrap
from datetime import datetime
import json

from eduid_userdb.exceptions import UserOutOfSync
from eduiddashboard.verifications import verify_nin, save_as_verified
from eduiddashboard.idproofinglog import LetterProofing
from eduiddashboard.session import _get_user_by_eppn

import logging
logger = logging.getLogger(__name__)

__author__ = 'lundberg'

"""
Verify a NIN for a letter verification that has failed due to a worker timeout.
"""

default_config_file = '/opt/eduid/eduid-dashboard/etc/eduid-dashboard.ini'


def verify_code(env, user, verification_doc):
    """
    :param env: Pyramid wsgi env
    :param user: Dashboard user
    :type user: eduid_userdb.dashboard.User
    :param verification_doc: Mongo doc
    :type verification_doc: dict
    """
    reference = unicode(verification_doc['_id'])
    obj_id = verification_doc['obj_id']

    if not obj_id:
        print "Could not find nin in verification object {!r}".format(verification_doc)
        sys.exit(1)

    assert_error_msg = 'Requesting users ID does not match verifications user ID'
    assert user.get_id() == verification_doc['user_oid'], assert_error_msg

    user, msg = verify_nin(env['request'], user, obj_id, reference)

    try:
        user.save(env['request'])
        print "Verified NIN saved for user {!r}.".format(user)
        verified = {
            'verified': True,
            'verified_timestamp': datetime.utcnow()
        }
        verification_doc.update(verified)
        env['request'].db.verifications.update({'_id': verification_doc['_id']}, verification_doc)
        print "Verifications doc ({!s}) marked as verified".format(reference)
    except UserOutOfSync:
        print "Verified NIN NOT saved for user {!r}. User out of sync.".format(user)
        sys.exit(1)


def letter_proof_user():
    description = """\
    Apply verification returned by eduid-idproofing-letter after failure. The JSON data is found in the
    eduid-idproofing-letter log after a users successful verification.
    Example:
    'letter_proof_user eppn idproofing-letter-json-data'
    """
    usage = "usage: %prog eppn idproofing-letter-json-data"
    parser = optparse.OptionParser(
        usage=usage,
        description=textwrap.dedent(description)
        )

    options, args = parser.parse_args(sys.argv[1:])
    if not len(args) == 2:
        print('Two arguments required')
        print(usage)
        return 2

    env = bootstrap(default_config_file)
    eppn = args[0]
    data = args[1]
    rdata = json.loads(data)
    user = _get_user_by_eppn(env['request'], eppn, legacy_user=True)

    if not user.get_nins() and rdata.get('verified', False):
        # Save data from successful verification call for later addition to user proofing collection
        rdata['created_ts'] = datetime.utcfromtimestamp(int(rdata['created_ts']))
        rdata['verified_ts'] = datetime.utcfromtimestamp(int(rdata['verified_ts']))
        letter_proofings = user.get_letter_proofing_data()
        letter_proofings.append(rdata)
        user.set_letter_proofing_data(letter_proofings)
        # Look up users official address at the time of verification per Kantara requirements
        print "Looking up address via Navet for user {!r}.".format(user)
        user_postal_address = env['request'].msgrelay.get_full_postal_address(rdata['number'])
        print "Finished looking up address via Navet for user {!r}.".format(user)
        proofing_data = LetterProofing(user, rdata['number'], rdata['official_address'],
                                       rdata['transaction_id'], user_postal_address)
        # Log verification event and fail if that goes wrong
        print "Logging proofing data for user {!r}.".format(user)
        if env['request'].idproofinglog.log_verification(proofing_data):
            print "Finished logging proofing data for user {!r}.".format(user)
            try:
                # This is a hack to reuse the existing proofing functionality, the users code is
                # verified by the micro service
                verify_nin(env['request'], user, rdata['number'])
                save_as_verified(env['request'], 'norEduPersonNIN', user.get_id(), rdata['number'])
                print "Verified NIN by physical letter saved for user {!r}.".format(user)
            except UserOutOfSync:
                print "Verified NIN by physical letter NOT saved for user {!r}. User out of sync.".format(user)
            else:
                print 'You have successfully verified the identity for user {!r}'.format(user)
    else:
        print 'User {!r} already has verified NIN ({!s}).'.format(user, user.get_nins())
