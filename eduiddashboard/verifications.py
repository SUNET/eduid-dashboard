from datetime import datetime, timedelta

from bson.tz_util import utc

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
        filters['user_oid'] = user['_id']
    log.debug("Verification code lookup filters : {!r}".format(filters))
    result = request.db.verifications.find_one(filters)
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
        "user_oid": user['_id'],
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
        'user_oid': user['_id'],
        'model_name': model_name,
        'verified': False,
    })


def verificate_code(request, model_name, code):
    from eduiddashboard.views.emails import mark_as_verified_email
    from eduiddashboard.views.mobiles import mark_as_verified_mobile
    from eduiddashboard.views.nins import mark_as_verified_nin, post_verified_nin

    verifiers = {
        'mailAliases': mark_as_verified_email,
        'mobile': mark_as_verified_mobile,
        'norEduPersonNIN': mark_as_verified_nin,
    }

    post_verifiers = {
        'norEduPersonNIN': post_verified_nin,
    }

    result = request.db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "code": code,
        }, {
            "$set": {
                "verified": True
            }
        },
        new=True,
        safe=True
    )
    if not result:
        return None
    obj_id = result['obj_id']
    if obj_id:
        user = request.userdb.get_user_by_oid(result['user_oid'])
        # Callback to a function which marks as verificated the proper user
        # attribute
        verifiers[model_name](request, user, obj_id)
        post_verified = post_verifiers.get(model_name, None)
        if post_verified is not None:
            post_verified(request, user, obj_id)
        # Do the save staff
        request.db.profiles.save(user, safe=True)
        request.context.propagate_user_changes(user)
    return obj_id


def save_as_verificated(request, model_name, user_oid, obj_id):
    from eduiddashboard.views.nins import post_verified_nin

    post_verifiers = {
        'norEduPersonNIN': post_verified_nin,
    }

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
    if obj_id:
        user = request.userdb.get_user_by_oid(result['user_oid'])
        post_verified = post_verifiers.get(model_name, None)
        if post_verified is not None:
            post_verified(request, user, obj_id)
    return obj_id


def generate_verification_link(request, code, model):
    link = request.context.safe_route_url("verifications", model=model, code=code)
    return link
