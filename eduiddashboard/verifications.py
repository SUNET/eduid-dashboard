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


def verify_code(request, model_name, code):
    """
    Verify a code and act accordingly to the model_name ('norEduPersonNIN', 'mobile', or 'mailAliases').

    This is what turns an unconfirmed NIN/mobile/e-mail into a confirmed one.

    :param request: The HTTP request
    :param model_name: 'norEduPersonNIN', 'mobile', or 'mailAliases'
    :param code: The user supplied code
    :type request: webob.request.BaseRequest


    :return:
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

    if obj_id:
        msg = "Code {!r} ({!s}) marked as verified"
        log.debug(msg.format(code, str(obj_id)))

        if 'edit-user' in request.session:
            # non personal mode
            user = request.session['edit-user']
        elif 'user' in request.session:
            # personal mode
            user = request.session['user']
        else:
            # should not happen
            user = request.userdb.get_user_by_oid(this_verification['user_oid'])
            user.retrieve_modified_ts(request.db.profiles)
        assert user.get_id() == this_verification['user_oid']
        old_verified = request.db.verifications.find_one(
            {
                "model_name": model_name,
                "obj_id": this_verification['obj_id'],
                "verified": True
            })

        old_user = None
        if old_verified:
            old_user = request.userdb.get_user_by_oid(old_verified['user_oid'])
            old_user.retrieve_modified_ts(request.db.profiles)

        if model_name == 'norEduPersonNIN':
            if not old_user:
                old_user_doc = request.db.profiles.find_one({
                    'norEduPersonNIN': obj_id
                })
                if old_user_doc:
                    old_user = User(old_user_doc)
            if old_user:
                nins = [nin for nin in old_user.get_nins() if nin != obj_id]
                old_user.set_nins(nins)
                addresses = [a for a in old_user.get_addresses() if not a['verified']]
                old_user.set_addresses(addresses)
            user.add_verified_nin(obj_id)
            user.retrieve_address(request, obj_id)
            request.msgrelay.postal_address_to_transaction_audit_log(reference)

            # Reset session eduPersonIdentityProofing on NIN verification
            request.session['eduPersonIdentityProofing'] = None

            msg = _('National identity number {obj} verified')

        elif model_name == 'mobile':
            if not old_user:
                old_user_doc = request.db.profiles.find_one({
                    'mobile': {'$elemMatch': {'mobile': obj_id, 'verified': True}}
                })
                if old_user_doc:
                   old_user = User(old_user_doc)
            if old_user:
                mobiles = [m for m in old_user.get_mobiles() if m['mobile'] != obj_id]
                old_user.set_mobiles(mobiles)
            user.add_verified_mobile(obj_id)
            msg = _('Mobile {obj} verified')

        elif model_name == 'mailAliases':
            if not old_user:
                old_user_doc = request.db.profiles.find_one({
                    'mailAliases': {'email': obj_id, 'verified': True}
                })
                if old_user_doc:
                    old_user = User(old_user_doc)
            if old_user:
                if old_user.get_mail() == obj_id:
                    old_user.set_mail('')
                mails = [m for m in old_user.get_mail_aliases() if m['email'] != obj_id]
                old_user.set_mail_aliases(mails)
            user.add_verified_email(obj_id)
            msg = _('Email {obj} verified')

        try:
            user.save(request)
            if old_user:
                old_user.save(request)
            verified = {
                'verified': True,
                'verified_timestamp': datetime.utcnow()
            }
            this_verification.update(verified)
            request.db.verifications.update({'_id': this_verification['_id']}, this_verification)
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
