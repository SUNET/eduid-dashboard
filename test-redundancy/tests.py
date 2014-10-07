# -*- coding: utf-8 -*-
'''
Usage
-----

To execute these tests, we need to have two servers serving the eduid-dashboard
app, both configured to use the same MongoDB databases. The URLs at which
these server listen for HTTP requests must be set below as
``DASHBOARD_SERVER_1`` and ``DASHBOARD_SERVER_1``.
We must also configure ``SMTP_SERVER`` with an address (in the local machine
were the tests are going to run) that can be reached from both signup servers,
and we must configure the signup servers' ``mail.host`` and ``mail.port`` with
the corresponding values from ``SMTP_SERVER``.

Then we need a python environment were we have installed selenium and nose::

    $ virtualenv selenium
    $ cd selenium
    $ source bin/activate
    $ easy_install selenium
    $ easy_install nose

This environment doesn't need to have any of the eduID packages installed.
With this environment activated, we change to the ``test-redundancy``
directory (were this file is located) and run ``nosetests``::

    $ cd /path/to/eduid-signup/test-redundancy
    $ nosetests

'''
_author__ = 'eperez'

import unittest
import asyncore
import re
from multiprocessing import Process, Queue
from smtpd import SMTPServer
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pymongo


SMTP_SERVER = ('192.168.122.1', 2525)
DASHBOARD_SERVER_1 = 'http://192.168.122.1:6545'
DASHBOARD_SERVER_2 = 'http://192.168.122.1:6546'
BASE_USERNAME = 'johnsmith'
BASE_PASSWORD = '1234'
MONGO_URI = 'mongodb://192.168.122.1:27017/'
MONGO_DB = 'eduid_am'


TEST_USER = {
    'givenName': 'John',
    'sn': 'Smith',
    'displayName': 'John Smith',
    'norEduPersonNIN': ['197801011235'],
    'photo': 'https://pointing.to/your/photo',
    'preferredLanguage': 'en',
    'eduPersonPrincipalName': 'johnsmith',
    'eduPersonEntitlement': [
        'urn:mace:eduid.se:role:admin',
        'urn:mace:eduid.se:role:student',
    ],
    'maxReachedLoa': 3,
    'mobile': [{
        'mobile': '+34609609609',
        'verified': True
    }, {
        'mobile': '+34 6096096096',
        'verified': False
    }],
    'mail': 'johnsmith@example.com',
    'mailAliases': [{
        'email': 'johnsmith@example.com',
        'verified': True,
    }, {
        'email': 'johnsmith2@example.com',
        'verified': True,
    }, {
        'email': 'johnsmith3@example.com',
        'verified': False,
    }],
    'postalAddress': [{
        'type': 'home',
        'country': 'SE',
        'address': "Long street, 48",
        'postalCode': "123456",
        'locality': "Stockholm",
        'verified': True,
    }, {
        'type': 'work',
        'country': 'ES',
        'address': "Calle Ancha, 49",
        'postalCode': "123456",
        'locality': "Punta Umbria",
        'verified': False,
    }],
}


class TestingSMTPServer(SMTPServer):

    def __init__(self, localaddr, remoteaddr, queue):
        SMTPServer.__init__(self, localaddr, remoteaddr)
        self.queue = queue

    def process_message(self, peer, mailfrom, rcpttos, data):
        self.queue.put(data)

def start_smtp_server(queue):
    TestingSMTPServer(SMTP_SERVER, None, queue)
    asyncore.loop()


class RedundancyTests(unittest.TestCase):

    queue = None
    smtp_process = None
    mongodb = None

    @classmethod
    def setUpClass(cls):
        cls.queue = Queue()
        cls.smtp_process = Process(target=start_smtp_server, args=(cls.queue,))
        cls.smtp_process.start()
        cls.conn = pymongo.MongoClient(host=MONGO_URI, tz_aware=True)

    @classmethod
    def tearDownClass(cls):
        cls.smtp_process.terminate()
        cls.smtp_process.join()
        cls.queue.close()
        cls.conn.close()

    def setUp(self):
        self.browser1 = webdriver.Firefox()
        self.browser2 = webdriver.Firefox()
        self.browser1.implicitly_wait(30)
        self.browser2.implicitly_wait(30)
        self.accept_next_alert = True
        self.conn[MONGO_DB].attributes.insert(TEST_USER)

    def tearDown(self):
        self.browser1.quit()
        self.browser2.quit()
        self.conn[MONGO_DB].attributes.find_and_modify(
                {'mail': 'johnsmith@example.com'},
                remove=True
                )
    
    def close_alert_and_get_its_text(self, browser):
        try:
            alert = browser.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True

    def clear_input(self, field):
        value = field.get_attribute('value')
        field.send_keys( [Keys.BACKSPACE] * len(value) )

    def login(self,
            username1=BASE_USERNAME, password1=BASE_PASSWORD,
            username2=BASE_USERNAME, password2=BASE_PASSWORD):
        self.browser1.get(DASHBOARD_SERVER_1)
        self.browser2.get(DASHBOARD_SERVER_2)
        self.assertIn('Enter your username and password', self.browser1.title)
        self.assertIn('Enter your username and password', self.browser2.title)
        username_field_1 = self.browser1.find_element_by_css_selector(
                '#username')
        password_field_1 = self.browser1.find_element_by_css_selector(
                '#password')
        username_field_1.send_keys(username1)
        password_field_1.send_keys(password1)
        self.browser1.find_element_by_css_selector(
                'input[type="submit"]').click()
        self.close_alert_and_get_its_text(self.browser1)
        username_field_2 = self.browser2.find_element_by_css_selector(
                '#username')
        password_field_2 = self.browser2.find_element_by_css_selector(
                '#password')
        username_field_2.send_keys(username2)
        password_field_2.send_keys(password2)
        self.browser2.find_element_by_css_selector(
                'input[type="submit"]').click()
        self.close_alert_and_get_its_text(self.browser2)
        self.assertIn('Profile', self.browser1.page_source)
        self.assertIn('Profile', self.browser2.page_source)

    def test_refresh_personal_data_edit(self):
        self.login()

        givenname_field1 = self.browser1.find_element_by_css_selector(
                '#deformField2')
        self.clear_input(givenname_field1)
        givenname_field1.send_keys(u'Enrique')
        self.browser1.find_element_by_css_selector(
                '#personaldataview-formsave').click()
        self.clear_input(givenname_field1)
        givenname_field1.send_keys(u'Pabló')
        self.browser1.find_element_by_css_selector(
                '#personaldataview-formsave').click()

        givenname_field2 = self.browser2.find_element_by_css_selector(
                '#deformField2')
        self.clear_input(givenname_field2)
        givenname_field2.send_keys(u'Alba')
        self.browser2.find_element_by_css_selector(
                '#personaldataview-formsave').click()

        self.assertIn('The user was out of sync. Please try again',
                self.browser2.page_source)
        
        givenname_field2 = self.browser2.find_element_by_css_selector(
                '#deformField2')
        self.assertEqual(givenname_field2.get_attribute('value'), u'Pabló')

    def test_confirm_email_address(self):
        self.login()

        self.browser1.find_element_by_css_selector(
                '.unstyled > li:nth-child(1) > a:nth-child(1)').click()

        self.browser1.find_element_by_css_selector(
                '.resend-code').click()
        data1 = self.queue.get(True, 1)
        pattern = re.compile(r'verificate/mailAliases/([^/]+)/')
        code = pattern.search(data1).group(1)
        code_input = self.browser1.find_element_by_css_selector(
                '#askDialogInput')
        code_input.send_keys(code)
        self.browser1.find_element_by_css_selector(
                '.modal-footer > a.ok-button').click()
        self.assertIn('An email address is pending confirmation',
                self.browser2.page_source)
        self.browser2.find_element_by_css_selector(
                '.unstyled > li:nth-child(1) > a:nth-child(1)').click()
        self.assertNotIn('An email address is pending confirmation',
                self.browser2.page_source)
