__author__ = 'mathiashedstrom'

from eduid_lookup_mobile.celery import app
from eduid_lookup_mobile.tasks import find_mobiles_by_NIN, find_NIN_by_mobile, verify_identity

class LookupMobileRelay(object):

    class TaskFailed(Exception):
        pass

    def __init__(self, settings):
        config = {
            'BROKER_URL': settings.get('lookup_mobile_broker_url',
                                       'amqp://eduid:eduid@127.0.0.1:5672/lookup_mobile'),
            'TEMPLATES_DIR': 'templates/',
            'CELERY_RESULT_BACKEND': 'amqp',
        }

        app.conf.update(config)

        self.settings = settings

        # set functions
        self._find_mobiles_by_NIN = find_mobiles_by_NIN
        self._find_NIN_by_mobile = find_NIN_by_mobile
        self._verify_identity = verify_identity

    def verify_identity(self, nin, verified_mobiles):
        try:
            result = self._verify_identity.delay(nin, verified_mobiles)
            # TODO How long timeout?
            result = result.get(timeout=15)
            return result
        except:
            raise self.TaskFailed('Something goes wrong')

    def find_NIN_by_mobile(self, mobile_number):
        try:
            result = self._find_NIN_by_mobile.delay(mobile_number)
            # TODO How long timeout?
            result = result.get(timeout=15)
            return result
        except:
            raise self.TaskFailed('Something goes wrong')

    def find_mobiles_by_NIN(self, nin):
        try:
            result = self._find_mobiles_by_NIN.delay(nin)
            # TODO How long timeout?
            result = result.get(timeout=15)
            return result
        except:
            raise self.TaskFailed('Something goes wrong')


def get_lookuprelay(request):
    return request.registry.settings['lookuprelay']