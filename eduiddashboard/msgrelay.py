from bson import ObjectId

from eduid_msg.celery import celery, get_message_relay
import eduid_msg.tasks  # flake8: noqa
from eduid_msg.tasks import send_message

import logging
logger = logging.getLogger(__name__)


TEMPLATES_RELATION = {
    'phone-validator': 'dummy',
    'nin-validator': 'dummy',
    'nin-reset-password': 'dummy',
}


class MsgRelay(object):

    def __init__(self, settings):

        config = {
            'BROKER_URL': settings.get('msg_broker_url',
                'amqp://eduid:eduid@127.0.0.1:5672/eduid_msg'),
            'TEMPLATES_DIR': 'templates/'
            # 'CELERY_RESULT_BACKEND': 'cache',
            # 'CELERY_CACHE_BACKEND': 'memory',
        }
        celery.conf.update(config)

        self._relay = get_message_relay(celery)
        self.settings = settings

    def get_content(self):
        return {
            'sitename': self.settings.get('site.name'),
            'sitelink': self.settings.get('personal_dashboard_base_url'),
        }

    def phone_validator(self, targetphone, code, language):
        content = self.get_content()
        content = {
            'code': code,
            'phonenumber': targetphone,

        }

        send_message.delay('sms', content, targetphone,
                           TEMPLATES_RELATION.get('phone-validator'),
                           language)

    def nin_validator(self, nin, code, language):
        content = self.get_content()

        content.update({
            'code': code,
        })
        send_message.delay('mm', content, nin,
                           TEMPLATES_RELATION.get('nin-validator'), language)

    def nin_reset_password(self, nin, code, link, language):
        content = self.get_content()
        content.update({
            'code': code,
            'link': link,
        })
        send_message.delay('mm', content, nin,
                           TEMPLATES_RELATION.get('nin-reset-password'),
                           language)


def get_msgrelay(request):
    return request.registry.settings['msgrelay']
