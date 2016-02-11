# -*- coding: utf-8 -*-

from eduid_userdb.dashboard import DashboardLegacyUser as OldUser, DashboardUser
from eduid_userdb import User
from eduid_am.celery import celery
from eduid_am.tasks import update_attributes_keep_result

import logging

logger = logging.getLogger(__name__)

__author__ = 'lundberg'


class AmRelay(object):

    class TaskFailed(Exception):
        pass

    def __init__(self, settings):

        config = settings.get('default_celery_conf')
        config.update({
            'BROKER_URL': settings.get('am_broker_url'),
        })
        celery.conf.update(config)

        self.settings = settings

    def request_sync(self, user):
        """
        Use Celery to ask eduid-am worker to propagate changes from our
        private DashboardUserDB into the central UserDB.

        :param user: User object

        :type user: DasboardLegacyUser or DashboardUser
        :return:
        """
        if isinstance(user, OldUser):
            user_id = str(user.get_id())
        elif isinstance(user, DashboardUser) or isinstance(user, User):
            user_id = str(user.user_id)
        else:
            raise ValueError('Can only propagate changes for DashboardLegacyUser, DashboardUser or User')

        # XXX this code is shared with signup, move somewhere common? Into eduid_am perhaps?
        logger.debug("Asking Attribute Manager to sync user {!s}".format(user))
        try:
            rtask = update_attributes_keep_result.delay('eduid_dashboard', user_id)
            result = rtask.get(timeout=3)
            logger.debug("Attribute Manager sync result: {!r}".format(result))
        except:
            logger.exception("Failed Attribute Manager sync request. trying again")
            try:
                rtask = update_attributes_keep_result.delay('eduid_dashboard', user_id)
                result = rtask.get(timeout=7)
                logger.debug("Attribute Manager sync result: {!r}".format(result))
                return result
            except:
                logger.exception("Failed Attribute Manager sync request retry")
                raise



