from datetime import datetime, timedelta

from bson.tz_util import utc

from pyramid.i18n import get_localizer

from eduid_am.user import User
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
    }
    request.db.verifications.find_and_modify(
        obj,
        {"$set": {
            "code": code,
            "verified": False,
            "timestamp": datetime.now(utc),
        }},
        upsert=True,
        safe=True,
    )

    session_verifications = request.session.get('verifications', [])
    session_verifications.append(code)
    request.session['verifications'] = session_verifications

    return code


def get_not_verificated_objects(request, model_name, user):
    return request.db.verifications.find({
        'user_oid': user.get_id(),
        'model_name': model_name,
        'verified': False,
    })


def verify_code(request, model_name, code):

    unverified = request.db.verifications.find_one(
        {
            "model_name": model_name,
            "code": code,
        })

    if not unverified:
        log.debug("Could not find un-verified code {!r}, model {!r}".format(code, model_name))
        return

    data = unverified['obj_id']

    if not data:
        return

    log.debug("Processing {!r} code {!r} ({!s})".format(model_name, code, str(data)))

    user = request.userdb.get_user_by_oid(unverified['user_oid'])
    old_verified = request.db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "obj_id": data,
            "verified": True,
        },
        remove=True)

    old_user = None
    if old_verified:
        old_user = request.userdb.get_user_by_oid(old_verified['user_oid'])

    if model_name == 'norEduPersonNIN':
        if not old_user:
            old_user_doc = request.db.profiles.find_one({
                'norEduPersonNIN': data
            })
            if old_user_doc:
                old_user = User(old_user_doc)
        if old_user:
            log.debug("Removing NIN {!r} from old_user {!r}".format(User.get_id()))
            nins = [nin for nin in old_user.get_nins() if nin != data]
            old_user.set_nins(nins)
            # Remove postal address too, since that is based on the NIN
            addresses = [a for a in old_user.get_addresses() if not a['verified']]
            old_user.set_addresses(addresses)
        user.add_verified_nin(data)
        user.retrieve_address(request, data)

        # Reset session eduPersonIdentityProofing on NIN verification
        request.session['eduPersonIdentityProofing'] = None

        msg = _('National identity number {obj} verified')

    elif model_name == 'mobile':
        if not old_user:
            old_user_doc = request.db.profiles.find_one({
                'mobile': {'$elemMatch': {'mobile': data, 'verified': True}}
            })
            if old_user_doc:
                old_user = User(old_user_doc)
        if old_user:
            mobiles = [m for m in old_user.get_mobiles() if m['mobile'] != data]
            old_user.set_mobiles(mobiles)
        user.add_verified_mobile(data)
        msg = _('Mobile {obj} verified')

    elif model_name == 'mailAliases':
        if not old_user:
            old_user_doc = request.db.profiles.find_one({
                'mailAliases': {'email': data, 'verified': True}
            })
            if old_user_doc:
                old_user = User(old_user_doc)
        if old_user:
            if old_user.get_mail() == data:
                old_user.set_mail('')
            mails = [m for m in old_user.get_mail_aliases() if m['email'] != data]
            old_user.set_mail_aliases(mails)
        user.add_verified_email(data)
        msg = _('Email {obj} verified')

    msg = get_localizer(request).translate(msg)
    request.session.flash(msg.format(obj=data),
                          queue='forms')

    if old_user:
        old_user.save(request)

    user.save(request)
    request.db.verifications.update({'_id': unverified['_id']}, {'verified': True})

    return data


def save_as_verificated(request, model_name, user_oid, obj_id):

    old_verified = request.db.verifications.find(
        {
            "model_name": model_name,
            "verified": True,
            "obj_id": obj_id,
        })
    if old_verified['user_oid'] == user_oid:
        return

    request.db.verifications.find_and_modify(
        {
            '_id': old_verified['_id']
        },
        remove=True)


    result = request.db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "user_oid": user_oid,
            "obj_id": obj_id,
        }, {
            "$set": {
                "verified": True,
                "timestamp": datetime.now(utc),
            }
        },
        new=True,
        safe=True
    )
    obj_id = result['obj_id']
    if obj_id and model_name == 'norEduPersonNIN':
        user = request.userdb.get_user_by_oid(result['user_oid'])
        user.retrieve_address(request, obj_id)
        user.save(request)
    return obj_id


def generate_verification_link(request, code, model):
    link = request.context.safe_route_url("verifications", model=model, code=code)
    return link
