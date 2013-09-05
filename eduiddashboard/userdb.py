
from eduid_am.celery import celery, get_attribute_manager
from eduid_am.exceptions import UserDoesNotExist, MultipleUsersReturned
import eduid_am.tasks  # flake8: noqa

from eduiddashboard.saml2.userdb import IUserDB


class UserDB(IUserDB):

    def __init__(self, settings):

        am_settings = {'MONGO_URI': settings['mongo_uri_am']}

        mongo_replicaset = settings.get('mongo_replicaset', None)

        if mongo_replicaset is not None:
            am_settings['replicaSet'] = mongo_replicaset

        celery.conf.update(am_settings)
        self._db = get_attribute_manager(celery)

        self.user_main_attribute = settings.get('saml2.user_main_attribute',
                                                'email')

    def get_user(self, userid):
        try:
            return self._db.get_user_by_field(
                self.user_main_attribute, userid)
        except UserDoesNotExist:
            raise self.UserDoesNotExist()
        except MultipleUsersReturned:
            raise self.MultipleUsersReturned()

    def exists_by_field(self, field, value):
        return self._db.exists_by_field(field, value)

    def get_users(self, filter, proyection=None):
        return self._db.get_users(filter, proyection)


def get_userdb(request):
    return request.registry.settings['userdb']
