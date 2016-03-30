from datetime import datetime, timedelta

from bson.tz_util import utc

from pyramid.i18n import get_localizer

from eduid_userdb.nin import Nin, NinList
from eduid_userdb.mail import MailAddress, MailAddressList
from eduid_userdb.phone import PhoneNumber, PhoneNumberList
from eduid_userdb.element import DuplicateElementViolation
from eduid_userdb.dashboard import DashboardLegacyUser as OldUser
from eduid_userdb.dashboard import DashboardUser
from eduid_userdb.exceptions import UserOutOfSync
from eduid_userdb.exceptions import UserDoesNotExist
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
    filters = {
        'model_name': model_name,
    }
    if obj_id is not None:
        filters['obj_id'] = obj_id
    if code is not None:
        filters['code'] = code
    if user is not None:
        filters['user_oid'] = user.user_id
    log.debug("Verification code lookup filters : {!r}".format(filters))
    result = request.db.verifications.find_one(filters)
    if result:
        expiration_timeout = request.registry.settings.get('verification_code_timeout')
        expire_limit = datetime.now(utc) - timedelta(minutes=int(expiration_timeout))
        result['expired'] = result['timestamp'] < expire_limit
        log.debug("Verification lookup result : {!r}".format(result))
    return result


def new_verification_code(request, model_name, obj_id, user, hasher=None):
    if hasher is None:
        hasher = get_unique_hash
    code = hasher()
    obj = {
        "model_name": model_name,
        "obj_id": obj_id,
        "user_oid": user.user_id,
        "code": code,
        "verified": False,
        "timestamp": datetime.now(utc),
    }
    doc_id = request.db.verifications.insert(obj)
    reference = unicode(doc_id)
    session_verifications = request.session.get('verifications', [])
    session_verifications.append(code)
    request.session['verifications'] = session_verifications
    log.info('Created new {!s} verification code for user {!r}.'.format(model_name, user))
    log.debug('Verification object id {!s}. Code: {!s}.'.format(obj_id, code))
    return reference, code


def get_not_verified_objects(request, model_name, user):
    return request.db.verifications.find({
        'user_oid': user.user_id,
        'model_name': model_name,
        'verified': False,
    })


def verify_nin(request, user, new_nin, reference=None):
    log.info('Trying to verify NIN for user {!r}.'.format(user))
    log.debug('NIN: {!s}.'.format(new_nin))
    # Start by removing nin from any other user
    old_user = request.dashboard_userdb.get_user_by_nin(new_nin, raise_on_missing=False)
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        log.debug('Found old user {!r} with NIN ({!s}) already verified.'.format(old_user, new_nin))
        log.debug('Old user NINs BEFORE: {!r}.'.format(old_user.nins.to_list()))
        if old_user.nins.primary.key == new_nin:
            old_nins = old_user.nins.verified.to_list()
            for nin in old_nins:
                if nin.key != new_nin:
                    old_user.nins.primary = nin.key
                    break
        old_user.nins.remove(new_nin)
        log.debug('Old user NINs AFTER: {!r}.'.format(old_user.nins.to_list()))
        request.context.save_dashboard_user(old_user)
        log.info('Removed NIN and associated addresses from user {!r}.'.format(old_user))
        steal_count = 1
    # Add the verified nin to the requesting user
    if user.nins.verified.count == 0:
        primary = True
    else:
        primary = False
    new_nin_obj = Nin(number=new_nin, application='dashboard',
            verified=True, primary=primary)
    try:
        user.nins.add(new_nin_obj)
    except DuplicateElementViolation:
        user.nins.find(new_nin).is_verified = True
    # Connect the verification to the transaction audit log
    if reference is not None:
        request.msgrelay.postal_address_to_transaction_audit_log(reference)
    # Reset session eduPersonIdentityProofing on NIN verification
    request.session['eduPersonIdentityProofing'] = None
    log.info('NIN verified for user {!r}.'.format(user))
    request.stats.count('dashboard/verify_nin_stolen', steal_count)
    request.stats.count('dashboard/verify_nin_completed', 1)
    return user, _('National identity number {obj} verified')


def verify_mobile(request, user, new_mobile):
    log.info('Trying to verify phone number for user {!r}.'.format(user))
    log.debug('Phone number: {!s}.'.format(new_mobile))
    # Start by removing mobile number from any other user
    old_user = request.dashboard_userdb.get_user_by_phone(new_mobile, raise_on_missing=False)
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        log.debug('Found old user {!r} with phone number ({!s}) already verified.'.format(old_user, new_mobile))
        log.debug('Old user phone numbers BEFORE: {!r}.'.format(old_user.phone_numbers.to_list()))
        if old_user.phone_numbers.primary.key == new_mobile:
            old_numbers = old_user.phone_numbers.verified.to_list()
            for number in old_numbers:
                if number.key != new_mobile:
                    old_user.phone_numbers.primary = number.key
                    break
        old_user.phone_numbers.remove(new_mobile)
        log.debug('Old user phone numbers AFTER: {!r}.'.format(old_user.phone_numbers.to_list()))
        request.context.save_dashboard_user(old_user)
        log.info('Removed phone number from user {!r}.'.format(old_user))
        steal_count = 1
    # Add the verified mobile number to the requesting user
    new_mobile_obj = PhoneNumber(data={'number': new_mobile,
                                       'verified': True,
                                       'primary': False})
    log.debug('User had phones BEFORE verification: {!r}'.format(user.phone_numbers.to_list()))
    if user.phone_numbers.primary is None:
        log.debug('Setting NEW phone number to primary: {}.'.format(new_mobile_obj))
        new_mobile_obj.is_primary = True
    try:
        user.phone_numbers.add(new_mobile_obj)
    except DuplicateElementViolation:
        user.phone_numbers.find(new_mobile).is_verified = True
    log.info('Phone number verified for user {!r}.'.format(user))
    request.stats.count('dashboard/verify_mobile_stolen', steal_count)
    request.stats.count('dashboard/verify_mobile_completed', 1)
    return user, _('Phone {obj} verified')


def verify_mail(request, user, new_mail):
    log.info('Trying to verify mail address for user {!r}.'.format(user))
    log.debug('Mail address: {!s}.'.format(new_mail))
    # Start by removing mail address from any other user
    old_user = request.dashboard_userdb.get_user_by_mail(new_mail, raise_on_missing=False)
    steal_count = 0
    if old_user and old_user.user_id != user.user_id:
        retrieve_modified_ts(old_user, request.dashboard_userdb)
        log.debug('Found old user {!r} with mail address ({!s}) already verified.'.format(old_user, new_mail))
        log.debug('Old user mail BEFORE: {!s}.'.format(old_user.mail_addresses.primary.key))
        log.debug('Old user mail aliases BEFORE: {!r}.'.format(old_user.mail_addresses.to_list()))
        if old_user.mail_addresses.primary.key == new_mail:
            old_addresses = old_user.mail_addresses.to_list()
            for address in old_addresses:
                if address.is_verified and address.key != new_mail:
                    old_user.mail_addresses.primary = address.key
                    break
        old_user.mail_addresses.remove(new_mail)
        if old_user.mail_addresses.primary is not None:
            log.debug('Old user mail AFTER: {!s}.'.format(old_user.mail_addresses.primary.key))
        if old_user.mail_addresses.count > 0:
            log.debug('Old user mail aliases AFTER: {!r}.'.format(old_user.mail_addresses.to_list()))
        else:
            log.debug('Old user has NO mail AFTER.')
        request.context.save_dashboard_user(old_user)
        steal_count = 1
    # Add the verified mail address to the requesting user
    new_email = MailAddress(email=new_mail, application='dashboard',
            verified=True, primary=False)
    if user.mail_addresses.primary is None:
        new_email.is_primary = True
    try:
        user.mail_addresses.add(new_email)
    except DuplicateElementViolation:
        user.mail_addresses.find(new_mail).is_verified = True
    log.info('Mail address verified for user {!r}.'.format(user))
    request.stats.count('dashboard/verify_mail_stolen', steal_count)
    request.stats.count('dashboard/verify_mail_completed', 1)
    return user, _('Email {obj} verified'.format(obj=new_mail))


def verify_code(request, model_name, code):
    """
    Verify a code and act accordingly to the model_name ('norEduPersonNIN', 'phone', or 'mailAliases').

    This is what turns an unconfirmed NIN/mobile/e-mail into a confirmed one.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'mobile', or 'mailAliases'
    :param code: The user supplied code
    :type request: webob.request.BaseRequest
    :return: string of verified data
    """
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

    assert_error_msg = 'Requesting users ID does not match verifications user ID'
    assert user.user_id == this_verification['user_oid'], assert_error_msg

    if model_name == 'norEduPersonNIN':
        user, msg = verify_nin(request, user, obj_id, reference)
    elif model_name == 'phone':
        user, msg = verify_mobile(request, user, obj_id)
    elif model_name == 'mailAliases':
        user, msg = verify_mail(request, user, obj_id)
    else:
        raise NotImplementedError('Unknown validation model_name')

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
        request.stats.count('dashboard/verify_code_completed', 1)
    return obj_id


def save_as_verified(request, model_name, user_oid, obj_id):

    old_verified = request.db.verifications.find(
        {
            "model_name": model_name,
            "verified": True,
            "obj_id": obj_id,
        })

    for old in old_verified:
        if old['user_oid'] == user_oid:
            return obj_id
    # User was not verified before, create a verification document
    result = request.db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "user_oid": user_oid,
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
