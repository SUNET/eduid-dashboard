from eduiddashboard.utils import get_unique_hash

from eduiddashboard import log


def dummy_message(request, message):
    """
    This function is only for debugging propposing
    """
    log.debug('[DUMMY_MESSAGE]: {0}'.format(message))


def get_verification_code(db, model_name, obj_id):
    code = get_unique_hash()
    obj = {
        "model_name": model_name,
        "obj_id": obj_id,
        "code": code,
        "verified": False
    }
    db.verifications.find_and_modify(obj, obj, upsert=True, safe=True)
    return code


def verificate_code(db, model_name, code):
    result = db.verifications.find_and_modify(
        {
            "model_name": model_name,
            "code": code,
            "verified": False
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
    return result['obj_id']


def generate_verification_link(request, db, model, obj_id):
    code = get_verification_code(db, model, obj_id)
    link = request.route_url("verifications", model=model, code=code)
    return link
