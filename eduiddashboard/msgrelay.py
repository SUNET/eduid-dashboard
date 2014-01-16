from collections import OrderedDict

from eduid_msg.celery import celery, get_message_relay
import eduid_msg.tasks
from eduid_msg.tasks import send_message, is_reachable, get_postal_address

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


class DummyTask:

    def __init__(self, retval=True):
        self.retval = retval

    def apply(self, *args, **kwargs):
        return self.retval

    def delay(self, *args, **kwargs):
        return self.retval


def parse_address_dict(data):
    """
        The expected address format is:

            OrderedDict([
                (u'Name', OrderedDict([
                    (u'@xmlns:xsi', u'http://www.w3.org/2001/XMLSchema-instance'),
                    (u'GivenNameMarking', u'20'),
                    (u'GivenName', u'public name'),
                    (u'SurName', u'thesurname')
                ])),
                (u'OfficialAddress', OrderedDict([
                    (u'@xmlns:xsi', u'http://www.w3.org/2001/XMLSchema-instance'),
                    (u'Address2', u'StreetName 103'),
                    (u'PostalCode', u'74141'),
                    (u'City', u'STOCKHOLM')
                ]))
            ])


        The returned format is like this:
            {
                'Address2': u'StreetName 103',
                'PostalCode': u'74141',
                'City': u'STOCKHOLM',
            }
    """

    dataaddress = data.get('OfficialAddress', OrderedDict())

    address = {}
    for (key, value) in dataaddress.iteritems():
        if not key.startswith('@xmlns:'):
            address[key] = value
    return address


class MsgRelay(object):

    class TaskFailed(Exception):
        pass

    def __init__(self, settings):

        config = {
            'BROKER_URL': settings.get('msg_broker_url',
                                       'amqp://eduid:eduid@127.0.0.1:5672/eduid_msg'),
            'TEMPLATES_DIR': 'templates/',
            'CELERY_RESULT_BACKEND': 'amqp',
        }
        celery.conf.update(config)

        self._relay = get_message_relay(celery)
        self.settings = settings
        if self.settings.get('testing', False):
            self._send_message = DummyTask()
            self._is_reachable = DummyTask()
            self._get_postal_address = DummyTask()
        else:
            self._send_message = send_message
            self._is_reachable = is_reachable
            self._get_postal_address = get_postal_address

    def get_language(self, lang):
        return LANGUAGE_MAPPING.get(lang, 'en_US')

    def get_content(self):
        return {
            'sitename': self.settings.get('site.name'),
            'sitelink': self.settings.get('personal_dashboard_base_url'),
        }

    def mobile_validator(self, targetphone, code, language):
        """
            The template keywords are:
                * sitename: (eduID by default)
                * sitelink: (the url dashboard in personal workmode)
                * code: the verification code
                * phonenumber: the phone number to verificate
        """
        content = self.get_content()
        content.update({
            'code': code,
            'phonenumber': targetphone,
        })
        lang = self.get_language(language)

        logger.debug('SENT mobile validator message code: {0} phone number: {1}'.format(
                     code, targetphone))
        self._send_message.delay('sms', content, targetphone,
                                 TEMPLATES_RELATION.get('phone-validator'),
                                 lang)

    def nin_reachable(self, nin):

        if not self.settings.get('testing', False):
            # We want to do this by the Sync way, using the wait and get
            # methods to lock this process until the result is ready
            rtask = self._is_reachable.apply_async(args=[nin])
            try:
                rtask.wait()
            except:
                raise self.TaskFailed('Something goes wrong')

            if rtask.successful():
                return rtask.get()
            else:
                raise self.TaskFailed('Something goes wrong')

        else:
            return self._is_reachable.apply_async(nin)

    def nin_validator(self, nin, code, language):
        """
            The template keywords are:
                * sitename: eduID by default
                * sitelink: the url dashboard in personal workmode
                * code: the verification code
                * nin: the nin number to verificate
        """
        content = self.get_content()

        content.update({
            'code': code,
            'nin': nin,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin message code: {0} NIN: {1}'.format(
                     code, nin))
        self._send_message.delay('mm', content, nin,
                                 TEMPLATES_RELATION.get('nin-validator'), lang)

    def nin_reset_password(self, nin, code, link, language):
        """
            The template keywords are:
                * sitename: eduID by default
                * sitelink: the url dashboard in personal workmode
                * nin: the inbox nin
                * code: the verification code
                * link: a link to verificate the code
        """
        content = self.get_content()
        content.update({
            'nin': nin,
            'code': code,
            'link': link,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin reset password message code: {0} NIN: {1}'.format(
                     code, nin))
        self._send_message.delay('mm', content, nin,
                                 TEMPLATES_RELATION.get('nin-reset-password'),
                                 lang)

    def get_postal_address(self, nin):
        """
            The expected address format is:

                OrderedDict([
                    (u'Name', OrderedDict([
                        (u'@xmlns:xsi', u'http://www.w3.org/2001/XMLSchema-instance'),
                        (u'GivenNameMarking', u'20'),
                        (u'GivenName', u'personal name'),
                        (u'SurName', u'thesurname')
                    ])),
                    (u'OfficialAddress', OrderedDict([
                        (u'@xmlns:xsi', u'http://www.w3.org/2001/XMLSchema-instance'),
                        (u'Address2', u'StreetName 103'),
                        (u'PostalCode', u'74141'),
                        (u'City', u'STOCKHOLM')
                    ]))
                ])


            The returned format is like this:
                {
                    'Address2': u'StreetName 103',
                    'PostalCode': u'74141',
                    'City': u'STOCKHOLM',
                }
        """

        if not self.settings.get('testing', False):
            rtask = self._get_postal_address.apply_async(args=[nin])
            try:
                rtask.wait()
            except:
                raise self.TaskFailed('Something goes wrong')

            if rtask.successful():
                result = rtask.get()
                return parse_address_dict(result)
            else:
                raise self.TaskFailed('Something goes wrong')

        else:
            # Return a sample if the testing is True
            return {
                'Address2': u'StreetName 103',
                'PostalCode': u'74141',
                'City': u'STOCKHOLM',
            }


def get_msgrelay(request):
    return request.registry.settings['msgrelay']
