from collections import OrderedDict

from eduid_msg.celery import celery, get_message_relay
from eduid_msg.tasks import send_message, is_reachable, get_postal_address, set_audit_log_postal_address, get_relations_to

import logging
logger = logging.getLogger(__name__)

TEMPLATES_RELATION = {
    'phone-validator': 'dummy',
    'nin-validator': 'nin-confirm',
    'nin-reset-password': 'nin-reset-password',
}


LANGUAGE_MAPPING = {
    'en': 'en_US',
    'sv': 'sv_SE',
}


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
            'CELERY_TASK_SERIALIZER': 'json',
            'MONGO_URI': settings.get('mongo_uri'),  # only needed when testing I think
        }
        celery.conf.update(config)

        self._relay = get_message_relay(celery)
        self.settings = settings
        self._send_message = send_message
        self._is_reachable = is_reachable
        self._get_postal_address = get_postal_address
        self._get_relations_to = get_relations_to
        self._set_audit_log_postal_address = set_audit_log_postal_address

    def get_language(self, lang):
        return LANGUAGE_MAPPING.get(lang, 'en_US')

    def get_content(self):
        return {
            'sitename': self.settings.get('site.name'),
            'sitelink': self.settings.get('personal_dashboard_base_url'),
        }

    def mobile_validator(self, reference, targetphone, code, language):
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

        logger.debug('SENT mobile validator message code: {0} phone number: {1} with reference {2}'.format(
                     code, targetphone, reference))
        self._send_message.delay('sms', reference, content, targetphone,
                                 TEMPLATES_RELATION.get('phone-validator'),
                                 lang)

    def nin_reachable(self, nin):

        # We want to do this by the Sync way, using the wait and get
        # methods to lock this process until the result is ready

        rtask = self._is_reachable.apply_async(args=[nin])
        try:
            rtask.wait()
        except:
            raise self.TaskFailed('Something went wrong')

        if rtask.successful():
            return rtask.get()
        else:
            raise self.TaskFailed('Something went wrong')

    def nin_validator(self, reference, nin, code, language, recipient, message_type='mm'):
        """
            The template keywords are:
                * sitename: eduID by default
                * sitelink: the url dashboard in personal workmode
                * code: the verification code
                * nin: the nin number to verificate
                * message_type: the type of message to send the verification code. Can only have values 'sms' or 'mm'
        """
        content = self.get_content()

        content.update({
            'code': code,
            'nin': nin,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin message reference: {0}, code: {1}, NIN: {2}'.format(
                     reference, code, nin))
        self._send_message.delay(message_type, reference, content, recipient,
                                 TEMPLATES_RELATION.get('nin-validator'), lang)

    def nin_reset_password(self, reference, nin, email, link, password_reset_timeout, language):
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
            'email': email,
            'reset_password_link': link,
            'password_reset_timeout': password_reset_timeout,
        })
        lang = self.get_language(language)
        logger.debug('SENT nin reset link message: {0} NIN: {1}'.format(
                     link, nin))
        self._send_message.delay('mm', str(reference), content, nin, TEMPLATES_RELATION.get('nin-reset-password'), lang)

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

        rtask = self._get_postal_address.apply_async(args=[nin])
        try:
            rtask.wait()
        except:
            raise self.TaskFailed('Something went wrong')

        if rtask.successful():
            result = rtask.get()
            return parse_address_dict(result)
        else:
            raise self.TaskFailed('Something went wrong')

    def get_full_postal_address(self, nin):
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
        """

        rtask = self._get_postal_address.apply_async(args=[nin])
        try:
            rtask.wait()
        except:
            raise self.TaskFailed('Something went wrong')

        if rtask.successful():
            result = rtask.get()
            return result
        else:
            raise self.TaskFailed('Something went wrong')

    def get_relations_to(self, nin, relative_nin):
        """
        Get a list of the NAVET 'Relations' type codes between a NIN and a relatives NIN.

        Known codes:
            M = spouse (make/maka)
            B = child (barn)
            FA = father
            MO = mother
            VF = some kind of legal guardian status. Childs typically have ['B', 'VF'] it seems.

        :param nin: Swedish National Identity Number
        :param relative_nin: Another Swedish National Identity Number
        :type nin: str | unicode
        :type relative_nin: str | unicode
        :return: List of codes. Empty list if the NINs are not related.
        :rtype: [str | unicode]
        """
        rtask = self._get_relations_to.apply_async(args=[nin, relative_nin])
        try:
            rtask.wait()
        except:
            raise self.TaskFailed('Something went wrong')

        if rtask.successful():
            result = rtask.get()
            return result
        else:
            raise self.TaskFailed('Something went wrong')

    def postal_address_to_transaction_audit_log(self, reference):
        """
            Adds the users postal address to the eduid_msg transaction log when validating a nin.
        """
        logger.debug('SENT postal address message for transaction log with reference: {0}'.format(reference))
        self._set_audit_log_postal_address.delay(reference)


def get_msgrelay(request):
    return request.registry.settings['msgrelay']
