from hashlib import sha256

from eduid_am.celery import celery, get_attribute_manager
import eduid_am.tasks


def verify_auth_token(shared_key, public_word, token, generator=sha256):
    return token == generator("{0}{1}".format(shared_key, public_word)).hexdigest()


def get_am(request):

    settings = {'mongodb': request.registry.settings['mongo_uri_am']}

    mongo_replicaset = request.registry.settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        settings['replicaSet'] = mongo_replicaset

    celery.conf.update(settings)
    return get_attribute_manager(celery)
