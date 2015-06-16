from eduiddashboard.testing import LoggedInReguestTests
from eduiddashboard import read_mapping


class LocaleChangeTests(LoggedInReguestTests):

    def setUp(self, settings={}):

        super(LocaleChangeTests, self).setUp(settings=settings)
        self.default_language = 'en'

    def test_get_default_lang(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/profile/')
        lang_name = read_mapping(self.settings, 'available_languages')[self.default_language]
        self.assertIn('<span>{0}</span>'.format(lang_name),
                      response.body)

    def test_change_language_with_referer(self):
        self.set_logged(user='johnsmith@example.com')
        referer = 'http://localhost/profile/'
        response = self.testapp.get('/set_language/?lang=sv',
                                    extra_environ={
                                        'HTTP_REFERER': referer
                                    },
                                    status=302)
        self.assertEqual(response.location, referer)
        response = self.testapp.get(referer, status=200)
        lang_name = read_mapping(self.settings, 'available_languages')['sv']
        self.assertIn('<span>{0}</span>'.format(lang_name), response.body)

    def test_change_language_without_referer(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/set_language/?lang=sv', status=302)
        response = self.testapp.get('/profile/', status=200)
        self.assertIn('<span>Svenska</span>', response.body)

    def test_language_cookie(self):
        self.set_logged(user='johnsmith@example.com')
        self.testapp.set_cookie('lang', 'sv')
        response = self.testapp.get('/profile/',
                                    status=200)
        self.assertIn('<span>Svenska</span>', response.body)

    def test_change_language_not_available(self):
        self.set_logged(user='johnsmith@example.com')
        self.testapp.get('/set_language/?lang=ph', status=404)
