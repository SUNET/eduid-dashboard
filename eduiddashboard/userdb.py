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
        """
        Locate a user in the userdb using the main attribute (typically 'mail').
        The name of the main attribute can be influenced in __init__().

        :param userid: string
        :return: user as dict
        :raise self.UserDoesNotExist: No user match the search criteria
        :raise self.MultipleUsersReturned: More than one user matches the search criteria
        """
        return self.get_user_by_attr(self.user_main_attribute, userid)

    def get_user_by_oid(self, oid):
        """
        Locate a user in the userdb given the user's _id.

        :param oid: ObjectId() or string
        :return: user as dict
        :raise self.UserDoesNotExist: No user match the search criteria
        :raise self.MultipleUsersReturned: More than one user matches the search criteria
        """
        if not isinstance(oid, ObjectId):
            oid = ObjectId(oid)
        return self.get_user_by_attr('_id', oid)

    def get_user_by_attr(self, attr, value):
        """
        Locate a user in the userdb using any attribute and value.

        :param attr: The attribute to match on
        :param value: The value to match on
        :return: user as dict
        :raise self.UserDoesNotExist: No user match the search criteria
        :raise self.MultipleUsersReturned: More than one user matches the search criteria
        """
        logger.debug("Looking in {!r} for user with {!r} = {!r}".format(
            self._db, attr, value))
        try:
            user = self._db.get_user_by_field(attr, value)
            logger.debug("Found user {!r}".format(user))
            return user
        except UserDoesNotExist:
            logger.error("UserDoesNotExist, {!r} = {!r}".format(attr, value))
            raise self.UserDoesNotExist()
        except MultipleUsersReturned:
            logger.error("MultipleUsersReturned, {!r} = {!r}".format(attr, value))
            raise self.MultipleUsersReturned()

    def exists_by_field(self, field, value):
        return self._db.exists_by_field(field, value)

    def exists_by_filter(self, filter):
        return self._db.exists_by_filter(filter)

    def get_users(self, filter, proyection=None):
        return self._db.get_users(filter, proyection)

    def get_identity_proofing(self, user):
        return self._db.get_identity_proofing(user['_id'])


def get_userdb(request):
    return request.registry.settings['userdb']
