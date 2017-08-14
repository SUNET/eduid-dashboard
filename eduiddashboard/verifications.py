"""
Module to handle verification of nin, phone and mail addresses.

XXX when we 'steal' e-mail addresses from a user, we simply remove it. However,
we will only find the e-mail address on the user if it is verified. This is a
discrepancy between verified/unverified addresses, we ought to either

* remove both verified and non-verified elements
* never remove, but just downgrade to unverified
"""
from datetime import datetime, timedelta

from bson.tz_util import utc

from pyramid.i18n import get_localizer

from eduid_userdb.nin import Nin
from eduid_userdb.mail import MailAddress
from eduid_userdb.phone import PhoneNumber
from eduid_userdb.element import DuplicateElementViolation
from eduid_userdb.exceptions import UserOutOfSync, UserDBValueError
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import get_unique_hash
from eduiddashboard.utils import retrieve_modified_ts
from eduiddashboard.session import get_session_user
from eduiddashboard import log


def dummy_message(request, message):
    """
    This function is only for debugging purposes
    """
    log.debug('[DUMMY_MESSAGE]: {!s}'.format(message))


def get_verification_code(request, model_name, obj_id=None, code=None, user=None):
    """
    Match a user supplied code (`code') against an actual entry in the database.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'phone', or 'mailAliases'
    :param obj_id: The data covered by the verification, like the phone number or nin or ...
    :param code: User supplied code
    :param user: The user

    :type request: pyramid.request.Request
    :type model_name: str | unicode
    :type obj_id: str | unicode
    :type code: str | unicode
    :type user: User | OldUser

    :returns: Verification entry from the database
    :rtype: dict
    """
    assert model_name in ['norEduPersonNIN', 'phone', 'mailAliases']

    userid = None
    if user is not None:
        try:
            userid = user.user_id
        except AttributeError:
            userid = user.get_id()

    filters = {
        'model_name': model_name,
    }
    if obj_id is not None:
        filters['obj_id'] = obj_id
    if code is not None:
        filters['code'] = code
    if userid is not None:
        filters['user_oid'] = userid
    log.debug("Verification code lookup filters : {!r}".format(filters))
    result = request.db.verifications.find_one(filters)
    if result:
        expiration_timeout = request.registry.settings.get('verification_code_timeout')
        expire_limit = datetime.now(utc) - timedelta(minutes=int(expiration_timeout))
        result['expired'] = result['timestamp'] < expire_limit
        log.debug("Verification lookup result : {!r}".format(result))
    return result


def new_verification_code(request, model_name, obj_id, user, hasher=None):
    """
    Match a user supplied code (`code') against an actual entry in the database.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'phone', or 'mailAliases'
    :param obj_id: The data covered by the verification, like the phone number or nin or ...
    :param user: The user
    :param hasher: Callable used to generate the code

    :type request: pyramid.request.Request
    :type model_name: str | unicode
    :type obj_id: str | unicode
    :type user: User | OldUser
    :type hasher: callable
    """
    assert model_name in ['norEduPersonNIN', 'phone', 'mailAliases']

    try:
        userid = user.user_id
    except AttributeError:
        userid = user.get_id()

    if hasher is None:
        hasher = get_unique_hash
    code = hasher()
    obj = {
        'model_name': model_name,
        'obj_id': obj_id,
        'user_oid': userid,
        'code': code,
        'verified': False,
        'timestamp': datetime.now(utc),
    }
    doc_id = request.db.verifications.insert(obj)
    reference = unicode(doc_id)
    session_verifications = request.session.get('verifications', [])
    session_verifications.append(code)
    request.session['verifications'] = session_verifications
    log.info('Created new {!s} verification code for user {!r}.'.format(model_name, user))
    log.debug('Verification object id {!s}. Code: {!s}.'.format(obj_id, code))
    return reference, code


def set_nin_verified(request, user, new_nin, reference=None):
    """
    Mark a National Identity Number (NIN) as verified on a user.

    This process also includes *removing* the NIN from any other user
    that had it as a verified NIN.

    :param request: The HTTP request
    :param user: The user
    :param new_nin: The National Identity Number to mark as verified
    :param reference: A reference to the verification code - used for audit logging

    :type request: pyramid.request.Request
    :type user: User
    :type new_nin: str | unicode

    :return: Status message
    :rtype: str | unicode
    """
    log.info('Trying to verify NIN for user {!r}.'.format(user))
    log.debug('NIN: {!s}.'.format(new_nin))
    # Start by removing nin from any other user
    old_user = request.userdb_new.get_user_by_nin(new_nin, raise_on_missing=False)
    log.debug('Searched for NIN {!r} in {!s}: {!r}'.format(new_nin, request.userdb_new, old_user))
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        _remove_nin_from_user(new_nin, old_user)
        request.context.save_dashboard_user(old_user)
        log.info('Removed NIN and associated addresses from user {!r}.'.format(old_user))
        steal_count = 1
    # Add the verified nin to the requesting user
    _add_nin_to_user(new_nin, user)
    _nin_verified_transaction_audit(request, reference)
    log.info('NIN verified for user {!r}.'.format(user))
    request.stats.count('verify_nin_stolen', steal_count)
    request.stats.count('verify_nin_completed')
    return _('National identity number {obj} verified')


def _remove_nin_from_user(nin, user):
    """
    Remove a NIN from one user because it is being verified by another user.
    Part of set_nin_verified() above.
    """
    log.debug('Found old user {!r} with NIN ({!s}) already verified.'.format(user, nin))
    log.debug('Old user NINs BEFORE: {!r}.'.format(user.nins.to_list()))
    if user.nins.primary.number == nin:
        old_nins = user.nins.verified.to_list()
        for this in old_nins:
            if this.number != nin:
                user.nins.primary = this.number
                break
    user.nins.remove(nin)
    log.debug('Old user NINs AFTER: {!r}.'.format(user.nins.to_list()))
    return user


def _add_nin_to_user(new_nin, user):
    """
    Add a NIN to a user.
    Part of set_nin_verified() above.
    """
    primary = user.nins.verified.count == 0
    new_nin_obj = Nin(number = new_nin,
                      application = 'dashboard',
                      verified = True,
                      primary = primary,
                      )
    # Remove the NIN from the user if it is already there
    try:
        user.nins.remove(new_nin)
    except UserDBValueError:
        pass
    user.nins.add(new_nin_obj)


def _nin_verified_transaction_audit(request, reference):
    """
    Part of set_nin_verified above.
    """
    # Connect the verification to the transaction audit log
    if reference is not None:
        request.msgrelay.postal_address_to_transaction_audit_log(reference)
    # Reset session eduPersonIdentityProofing on NIN verification
    request.session['eduPersonIdentityProofing'] = None


def set_phone_verified(request, user, new_number):
    """
    Mark a phone number as verified on a user.

    This process also includes *removing* the phone number from any other user
    that had it as a verified phone number.

    :param request: The HTTP request
    :param user: The user
    :param new_number: The phone number to mark as verified

    :type request: pyramid.request.Request
    :type user: User
    :type new_number: str | unicode

    :return: Status message
    :rtype: str | unicode
    """
    log.info('Trying to verify phone number for user {!r}.'.format(user))
    log.debug('Phone number: {!s}.'.format(new_number))
    # Start by removing mobile number from any other user
    old_user = request.userdb_new.get_user_by_phone(new_number, raise_on_missing=False)
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        _remove_phone_from_user(new_number, old_user)
        request.context.save_dashboard_user(old_user)
        log.info('Removed phone number from user {!r}.'.format(old_user))
        steal_count = 1
    # Add the verified mobile number to the requesting user
    _add_phone_to_user(new_number, user)
    log.info('Phone number verified for user {!r}.'.format(user))
    request.stats.count('verify_mobile_stolen', steal_count)
    request.stats.count('verify_mobile_completed')
    return _('Phone {obj} verified')


def _remove_phone_from_user(number, user):
    """
    Remove a phone number from one user because it is being verified by another user.
    Part of set_phone_verified() above.
    """
    log.debug('Found old user {!r} with phone number ({!s}) already verified.'.format(user, number))
    log.debug('Old user phone numbers BEFORE: {!r}.'.format(user.phone_numbers.to_list()))
    if user.phone_numbers.primary.number == number:
        # Promote some other verified phone number to primary
        for phone in user.phone_numbers.verified.to_list():
            if phone.number != number:
                user.phone_numbers.primary = phone.number
                break
    user.phone_numbers.remove(number)
    log.debug('Old user phone numbers AFTER: {!r}.'.format(user.phone_numbers.to_list()))
    return user


def _add_phone_to_user(new_number, user):
    """
    Add a phone number to a user.
    Part of set_phone_verified() above.
    """
    phone = PhoneNumber(data={'number': new_number,
                              'verified': True,
                              'primary': False})
    log.debug('User had phones BEFORE verification: {!r}'.format(user.phone_numbers.to_list()))
    if user.phone_numbers.primary is None:
        log.debug('Setting NEW phone number to primary: {}.'.format(phone))
        phone.is_primary = True
    try:
        user.phone_numbers.add(phone)
    except DuplicateElementViolation:
        user.phone_numbers.find(new_number).is_verified = True


def set_email_verified(request, user, new_mail):
    """
    Mark an e-mail address as verified on a user.

    This process also includes *removing* the e-mail address from any other user
    that had it as a verified e-mail address.

    :param request: The HTTP request
    :param user: The user
    :param new_mail: The e-mail address to mark as verified

    :type request: pyramid.request.Request
    :type user: User
    :type new_mail: str | unicode

    :return: Status message
    :rtype: str | unicode
    """
    log.info('Trying to verify mail address for user {!r}.'.format(user))
    log.debug('Mail address: {!s}.'.format(new_mail))
    # Start by removing the email address from any other user that currently has it (verified)
    old_user = request.userdb_new.get_user_by_mail(new_mail, raise_on_missing=False)
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        old_user = _remove_mail_from_user(new_mail, old_user)
        request.context.save_dashboard_user(old_user)
        steal_count = 1
    # Add the verified mail address to the requesting user
    _add_mail_to_user(new_mail, user)
    log.info('Mail address verified for user {!r}.'.format(user))
    request.stats.count('verify_mail_stolen', steal_count)
    request.stats.count('verify_mail_completed')
    return _('Email {obj} verified')


def _remove_mail_from_user(email, user):
    """
    Remove an email address from one user because it is being verified by another user.
    Part of set_email_verified() above.
    """
    log.debug('Removing mail address {!s} from user {!s}'.format(email, user))
    if user.mail_addresses.primary:
        # only in the test suite could primary ever be None here
        log.debug('Old user mail BEFORE: {!s}'.format(user.mail_addresses.primary))
    log.debug('Old user mail aliases BEFORE: {!r}'.format(user.mail_addresses.to_list()))
    if user.mail_addresses.primary and user.mail_addresses.primary.email == email:
        # Promote some other verified e-mail address to primary
        for address in user.mail_addresses.to_list():
            if address.is_verified and address.email != email:
                user.mail_addresses.primary = address.email
                break
    user.mail_addresses.remove(email)
    if user.mail_addresses.primary is not None:
        log.debug('Old user mail AFTER: {!s}.'.format(user.mail_addresses.primary))
    if user.mail_addresses.count > 0:
        log.debug('Old user mail aliases AFTER: {!r}.'.format(user.mail_addresses.to_list()))
    else:
        log.debug('Old user has NO mail AFTER.')
    return user


def _add_mail_to_user(email, user):
    """
    Add an email address to a user.
    Part of set_email_verified() above.
    """
    new_email = MailAddress(email = email, application = 'dashboard',
                            verified = True, primary = False)
    if user.mail_addresses.primary is None:
        new_email.is_primary = True
    try:
        user.mail_addresses.add(new_email)
    except DuplicateElementViolation:
        user.mail_addresses.find(email).is_verified = True


def verify_code(request, model_name, code):
    """
    Verify a code and act accordingly to the model_name ('norEduPersonNIN', 'phone', or 'mailAliases').

    This is what turns an unconfirmed NIN/mobile/e-mail into a confirmed one.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'phone', or 'mailAliases'
    :param code: The user supplied code
    :type request: pyramid.request.Request
    :return: string of verified data
    """
    assert model_name in ['norEduPersonNIN', 'phone', 'mailAliases']

    this_verification = request.db.verifications.find_one(
        {
            "model_name": model_name,
            "code": code,
        })

    if not this_verification:
        log.error("Could not find verification record for code {!r}, model {!r}".format(code, model_name))
        return

    reference = unicode(this_verification['_id'])
    obj_id = this_verification['obj_id']

    if not obj_id:
        return None

    user = get_session_user(request, legacy_user=False)
    retrieve_modified_ts(user, request.dashboard_userdb)

    assert_error_msg = 'Requesting users ID does not match verifications user ID'
    assert user.user_id == this_verification['user_oid'], assert_error_msg

    if model_name == 'norEduPersonNIN':
        msg = set_nin_verified(request, user, obj_id, reference)
    elif model_name == 'phone':
        msg = set_phone_verified(request, user, obj_id)
    elif model_name == 'mailAliases':
        msg = set_email_verified(request, user, obj_id)
    else:
        raise NotImplementedError('Unknown validation model_name: {!r}'.format(model_name))

    try:
        request.context.save_dashboard_user(user)
        log.info("Verified {!s} saved for user {!r}.".format(model_name, user))
        verified = {
            'verified': True,
            'verified_timestamp': datetime.utcnow()
        }
        this_verification.update(verified)
        request.db.verifications.update({'_id': this_verification['_id']}, this_verification)
        log.info("Code {!r} ({!s}) marked as verified".format(code, obj_id))
    except UserOutOfSync:
        log.info("Verified {!s} NOT saved for user {!r}. User out of sync.".format(model_name, user))
        raise
    else:
        msg = get_localizer(request).translate(msg)
        request.session.flash(msg.format(obj=obj_id), queue='forms')
        request.stats.count('verify_code_completed')
    return obj_id


def save_as_verified(request, model_name, user, obj_id):
    """
    Update a verification code entry in the database, indicating it has been
    (successfully) used.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'phone', or 'mailAliases'
    :param user: The user
    :param obj_id: The data covered by the verification, like the phone number or nin or ...

    :type request: pyramid.request.Request
    :type model_name: str | unicode
    :type user: User | OldUser
    :type obj_id: str | unicode
    """
    try:
        userid = user.user_id
    except AttributeError:
        userid = user.get_id()

    assert model_name in ['norEduPersonNIN', 'phone', 'mailAliases']

    old_verified = request.db.verifications.find(
        {
            "model_name": model_name,
            "verified": True,
            "obj_id": obj_id,
        })

    for old in old_verified:
        if old['user_oid'] == userid:
            return obj_id
    # User was not verified before, create a verification document
    result = request.db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "user_oid": userid,
            "obj_id": obj_id,
        }, {
            "$set": {
                "verified": True,
                "timestamp": datetime.utcnow(),
            }
        },
        upsert=True,
        new=True
    )
    return result['obj_id']


def generate_verification_link(request, code, model):
    link = request.context.safe_route_url("verifications", model=model, code=code)
    return link
