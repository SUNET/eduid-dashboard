from bson import ObjectId

from eduid_am.celery import celery, get_attribute_manager
from eduid_am.exceptions import UserDoesNotExist, MultipleUsersReturned
import eduid_am.tasks  # flake8: noqa

from eduiddashboard.saml2.userdb import IUserDB

import logging
logger = logging.getLogger(__name__)


class UserDB(IUserDB):

    def __init__(self, settings):

        am_settings = {'MONGO_URI': settings['mongo_uri_am']}

        mongo_replicaset = settings.get('mongo_replicaset', None)

        if mongo_replicaset is not None:
            am_settings['replicaSet'] = mongo_replicaset

        celery.conf.update(am_settings)
        self._db = get_attribute_manager(celery)

        self.user_main_attribute = settings.get('saml2.user_main_attribute',
                                                'mail')

    def get_user(self, userid):
        try:
            logger.debug("Looking in {!r} for user with {!r} = {!r}".format(
                    self._db, self.user_main_attribute, userid))
            user = self._db.get_user_by_field(self.user_main_attribute, userid)
            logger.debug("Found user {!r}".format(user))
            return user
        except UserDoesNotExist:
            logger.error("UserDoesNotExist")
            raise self.UserDoesNotExist()
        except MultipleUsersReturned:
            logger.error("MultipleUsersReturned")
            raise self.MultipleUsersReturned()

    def get_user_by_oid(self, oid):
        if not isinstance(oid, ObjectId):
            oid = ObjectId(oid)
        try:
            logger.debug("Looking in {!r} for user with {!r} = {!r}".format(
                    self._db, '_id', oid))
            user = self._db.get_user_by_field('_id', oid)
            logger.debug("Found user {!r}".format(user))
            return user
        except UserDoesNotExist:
            logger.error("UserDoesNotExist")
            raise self.UserDoesNotExist()
        except MultipleUsersReturned:
            logger.error("MultipleUsersReturned")
            raise self.MultipleUsersReturned()

    def exists_by_field(self, field, value):
        return self._db.exists_by_field(field, value)

    def exists_by_filter(self, filter):
        return self._db.exists_by_filter(filter)

    def get_users(self, filter, proyection=None):
        return self._db.get_users(filter, proyection)


def get_userdb(request):
    return request.registry.settings['userdb']
