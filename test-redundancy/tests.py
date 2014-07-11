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


SMTP_SERVER = ('192.168.122.1', 2525)
DASHBOARD_SERVER_1 = 'http://192.168.122.1:6545'
DASHBOARD_SERVER_2 = 'http://192.168.122.1:6546'
BASE_USERNAME = 'eperez1'
BASE_PASSWORD = '1234'


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

    @classmethod
    def setUpClass(cls):
        cls.queue = Queue()
        cls.smtp_process = Process(target=start_smtp_server, args=(cls.queue,))
        cls.smtp_process.start()

    @classmethod
    def tearDownClass(cls):
        cls.smtp_process.terminate()
        cls.smtp_process.join()
        cls.queue.close()

    def setUp(self):
        self.browser1 = webdriver.Firefox()
        self.browser2 = webdriver.Firefox()
        self.browser1.implicitly_wait(30)
        self.browser2.implicitly_wait(30)
        self.accept_next_alert = True

    def tearDown(self):
        self.browser1.quit()
        self.browser2.quit()
    
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
        givenname_field1.send_keys(u'Pabló')
        self.browser1.find_element_by_css_selector(
                '#personaldataview-formsave').click()
        self.browser2.refresh()
        givenname_field2 = self.browser2.find_element_by_css_selector(
                '#deformField2')
        self.assertEqual(givenname_field2.get_attribute('value'), u'Pabló')

        self.browser1.refresh()
        givenname_field1 = self.browser1.find_element_by_css_selector(
                '#deformField2')
        self.clear_input(givenname_field1)
        givenname_field1.send_keys(u'Enrique')
        self.browser1.find_element_by_css_selector(
                '#personaldataview-formsave').click()
        self.browser2.refresh()
        givenname_field2 = self.browser2.find_element_by_css_selector(
                '#deformField2')
        self.assertEqual(givenname_field2.get_attribute('value'), u'Enrique')

