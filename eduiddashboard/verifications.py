from datetime import datetime, timedelta

from bson.tz_util import utc

from pyramid.i18n import get_localizer
from pyramid.httpexceptions import HTTPFound

from eduid_am.user import User
from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import get_unique_hash
from eduiddashboard import log


def dummy_message(request, message):
    """
    This function is only for debugging propposing
    """
    log.debug('[DUMMY_MESSAGE]: {0}'.format(message))


def get_verification_code(request, model_name, obj_id=None, code=None, user=None):
    filters = {
        'model_name': model_name,
    }
    if obj_id is not None:
        filters['obj_id'] = obj_id
    if code is not None:
        filters['code'] = code
    if user is not None:
        filters['user_oid'] = user.get_id()
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
        "user_oid": user.get_id(),
        "code": code,
        "verified": False,
        "timestamp": datetime.now(utc),
    }
    doc_id = request.db.verifications.insert(obj)
    reference = unicode(doc_id)
    session_verifications = request.session.get('verifications', [])
    session_verifications.append(code)
    request.session['verifications'] = session_verifications

    return reference, code


def get_not_verified_objects(request, model_name, user):
    return request.db.verifications.find({
        'user_oid': user.get_id(),
        'model_name': model_name,
        'verified': False,
    })


def verify_nin(request, user, new_nin, reference):
    # Start by removing nin from any other user
    old_user_docs = request.db.profiles.find({
        'norEduPersonNIN': new_nin
    })
    for old_user_doc in old_user_docs:
        old_user = User(old_user_doc)
        if old_user:
            nins = [nin for nin in old_user.get_nins() if nin != new_nin]
            old_user.set_nins(nins)
            addresses = [a for a in old_user.get_addresses() if not a['verified']]
            old_user.set_addresses(addresses)
            old_user.retrieve_modified_ts(request.db.profiles)
            old_user.save(request)
    # Add the verified nin to the requesting user
    user.add_verified_nin(new_nin)
    user.retrieve_address(request, new_nin)
    # Connect the verification to the transaction audit log
    request.msgrelay.postal_address_to_transaction_audit_log(reference)
    # Reset session eduPersonIdentityProofing on NIN verification
    request.session['eduPersonIdentityProofing'] = None
    return _('National identity number {obj} verified')


def verify_mobile(request, user, new_mobile):
    # Start by removing mobile number from any other user
    old_user_docs = request.db.profiles.find({
        'mobile': {'$elemMatch': {'mobile': new_mobile, 'verified': True}}
    })
    for old_user_doc in old_user_docs:
        old_user = User(old_user_doc)
        if old_user:
            mobiles = [m for m in old_user.get_mobiles() if m['mobile'] != new_mobile]
            old_user.set_mobiles(mobiles)
            old_user.retrieve_modified_ts(request.db.profiles)
            old_user.save(request)
    # Add the verified mobile number to the requesting user
    user.add_verified_mobile(new_mobile)
    return _('Mobile {obj} verified')


def verify_mail(request, user, new_mail):
    # Start by removing mail address from any other user
    old_user_docs = request.db.profiles.find({
        'mailAliases': {'email': new_mail, 'verified': True}
    })
    for old_user_doc in old_user_docs:
        old_user = User(old_user_doc)
        if old_user:
            if old_user.get_mail() == new_mail:
                old_user.set_mail('')
            mails = [m for m in old_user.get_mail_aliases() if m['email'] != new_mail]
            old_user.set_mail_aliases(mails)
            old_user.retrieve_modified_ts(request.db.profiles)
            old_user.save(request)
    # Add the verified mail address to the requesting user
    user.add_verified_email(new_mail)
    return _('Email {obj} verified')


def verify_code(request, model_name, code):
    """
    Verify a code and act accordingly to the model_name ('norEduPersonNIN', 'mobile', or 'mailAliases').

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
        log.debug("Could not find verification record for code {!r}, model {!r}".format(code, model_name))
        return

    reference = unicode(this_verification['_id'])
    obj_id = this_verification['obj_id']

    if not obj_id:
        return None

    if 'edit-user' in request.session:
        # non personal mode
        user = request.session['edit-user']
    elif 'user' in request.session:
        # personal mode
        user = request.session['user']

    assert_error_msg = 'Requesting users ID does not match verifications user ID'
    assert user.get_id() == this_verification['user_oid'], assert_error_msg

    if model_name == 'norEduPersonNIN':
        msg = verify_nin(request, user, obj_id, reference)
    elif model_name == 'mobile':
        msg = verify_mobile(request, user, obj_id)
    elif model_name == 'mailAliases':
        msg = verify_mail(request, user, obj_id)
    else:
        raise NotImplementedError('Unknown validation model_name')

    try:
        user.save(request)
        verified = {
            'verified': True,
            'verified_timestamp': datetime.utcnow()
        }
        this_verification.update(verified)
        request.db.verifications.update({'_id': this_verification['_id']}, this_verification)
        log.debug("Code {!r} ({!s}) marked as verified".format(code, str(obj_id)))
    except UserOutOfSync:
        raise
    else:
        msg = get_localizer(request).translate(msg)
        request.session.flash(msg.format(obj=obj_id), queue='forms')
    return obj_id


def save_as_verified(request, model_name, user_oid, obj_id):

    old_verified = request.db.verifications.find(
        {
            "model_name": model_name,
            "verified": True,
            "obj_id": obj_id,
        })
    n = old_verified.count()
    if n > 1:
        log.warn('Too many verifications ({}) for NIN {}'.format(n, obj_id))

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
