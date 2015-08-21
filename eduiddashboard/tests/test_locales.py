from eduiddashboard.testing import LoggedInRequestTests
from eduiddashboard import read_mapping


class LocaleChangeTests(LoggedInRequestTests):

    def setUp(self, settings={}):

        super(LocaleChangeTests, self).setUp(settings=settings)
        self.default_language = 'en'

    def test_get_default_lang(self):
        self.set_logged(email ='johnsmith@example.com')
        response = self.testapp.get('/profile/')
        lang_name = read_mapping(self.settings, 'available_languages')[self.default_language]
        response.mustcontain('<span>{0}</span>'.format(lang_name))

    def test_change_language_with_referer(self):
        self.set_logged(email = 'johnsmith@example.com')
        host = self.settings['dashboard_hostname']
        referer = 'http://{hostname}/profile/'.format(hostname=host)
        response = self.testapp.get('/set_language/?lang=sv',
                                    extra_environ={
                                        'HTTP_REFERER': referer,
                                        'HTTP_HOST': host
                                    },
                                    status=302)
        cookies = self.testapp.cookies
        self.assertIsNotNone(cookies.get('lang', None))
        self.assertEqual('sv', cookies.get('lang', None))
        self.assertEqual(referer, response.location)

    def test_change_language_with_invalid_referer(self):
        self.set_logged(email='johnsmith@example.com')
        host = self.settings['dashboard_hostname']
        dashboard_baseurl = self.settings['dashboard_baseurl']
        invalid_referer = 'http://attacker.controlled.site'
        response = self.testapp.get('/set_language/?lang=sv',
                                    extra_environ={
                                        'HTTP_REFERER': invalid_referer,
                                        'HTTP_HOST': host
                                    },
                                    status=302)
        cookies = self.testapp.cookies
        self.assertIsNotNone(cookies.get('lang', None))
        self.assertEqual('sv', cookies.get('lang', None))
        self.assertEqual(dashboard_baseurl, response.location)

    def test_change_language_with_invalid_host(self):
        self.set_logged(email = 'johnsmith@example.com')
        host = self.settings['dashboard_hostname']
        dashboard_baseurl = self.settings['dashboard_baseurl']
        referer = 'http://{hostname}/profile/'.format(hostname=host)
        invalid_host = 'attacker.controlled.site'
        response = self.testapp.get('/set_language/?lang=sv',
                                    extra_environ={
                                        'HTTP_REFERER': referer,
                                        'HTTP_HOST': invalid_host
                                    },
                                    status=302)
        cookies = self.testapp.cookies
        self.assertIsNotNone(cookies.get('lang', None))
        self.assertEqual('sv', cookies.get('lang', None))
        self.assertEqual(dashboard_baseurl, response.location)

    def test_change_language_without_referer(self):
        self.set_logged(email ='johnsmith@example.com')
        response = self.testapp.get('/set_language/?lang=sv', status=302)
        self.assertEqual('sv', self.testapp.cookies.get('lang', None))
        response = self.testapp.get('/profile/', status=200)
        cookies = self.testapp.cookies
        self.assertIsNotNone(cookies.get('lang', None))
        self.assertEqual('sv', cookies.get('lang', None))
        response.mustcontain('<span>Svenska</span>')

    def test_language_cookie(self):
        self.set_logged(email = 'johnsmith@example.com')
        self.testapp.set_cookie('lang', 'sv')
        response = self.testapp.get('/profile/', status=200)
        cookies = self.testapp.cookies
        self.assertIsNotNone(cookies.get('lang', None))

        # The cookie is escaped when setting the value manually
        # and therefore our assertion have to use the same
        # escaping around the value when testing it.
        self.assertEqual('"sv"', cookies.get('lang', None))

        response.mustcontain('<span>Svenska</span>')

    def test_change_language_not_available(self):
        self.set_logged(email ='johnsmith@example.com')
        self.testapp.get('/set_language/?lang=ph', status=404)
