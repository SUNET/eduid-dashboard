import os
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


LANGUAGE_MAPPING = {
    'en': 'en_US',
    'sv': 'sv_SE',
}


class DummyMessages:
    def delay(self, *args, **kwargs):
        pass


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
        if self.settings.get('testing', False):
            self.send_message = DummyMessages()
        else:
            self.send_message = send_message


    def get_language(self, lang):
        return LANGUAGE_MAPPING.get(lang, 'en_US')

    def get_content(self):
        return {
            'sitename': self.settings.get('site.name'),
            'sitelink': self.settings.get('personal_dashboard_base_url'),
        }

    def mobile_validator(self, targetphone, code, language):
        content = self.get_content()
        content = {
            'code': code,
            'phonenumber': targetphone,

        }
        lang = self.get_language(language)

        logger.debug('SENT mobile validator message code: {0} phone number: {1}'.format(
                     code, targetphone))
        self.send_message.delay('sms', content, targetphone,
                                TEMPLATES_RELATION.get('phone-validator'),
                                lang)

    def nin_validator(self, nin, code, language):
        content = self.get_content()

        content.update({
            'code': code,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin message code: {0} NIN: {1}'.format(
                     code, nin))
        self.send_message.delay('mm', content, nin,
                                TEMPLATES_RELATION.get('nin-validator'), lang)

    def nin_reset_password(self, nin, code, link, language):
        content = self.get_content()
        content.update({
            'code': code,
            'link': link,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin reset password message code: {0} NIN: {1}'.format(
                     code, nin))
        self.send_message.delay('mm', content, nin,
                                TEMPLATES_RELATION.get('nin-reset-password'),
                                lang)


def get_msgrelay(request):
    return request.registry.settings['msgrelay']
