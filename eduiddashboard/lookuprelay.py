from eduid_lookup_mobile.celery import app
from eduid_lookup_mobile.tasks import find_mobiles_by_NIN, find_NIN_by_mobile

__author__ = 'mathiashedstrom'

class LookupMobileRelay(object):

    class TaskFailed(Exception):
        pass

    def __init__(self, settings):

        config = settings.get('default_celery_conf')
        config.update({
            'BROKER_URL': settings.get('lookup_mobile_broker_url'),
            'TEMPLATES_DIR': 'templates/',
        })
        app.conf.update(config)

        self.settings = settings

        # set functions
        self._find_mobiles_by_NIN = find_mobiles_by_NIN
        self._find_NIN_by_mobile = find_NIN_by_mobile

    def find_NIN_by_mobile(self, mobile_number):
        try:
            result = self._find_NIN_by_mobile.delay(mobile_number)
            # TODO How long timeout?
            result = result.get(timeout=25)
            return result
        except:
            raise self.TaskFailed('Something went wrong')

    def find_mobiles_by_NIN(self, nin):
        try:
            result = self._find_mobiles_by_NIN.delay(nin)
            # TODO How long timeout?
            result = result.get(timeout=25)
            return result
        except:
            raise self.TaskFailed('Something went wrong')
