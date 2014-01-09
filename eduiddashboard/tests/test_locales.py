from eduiddashboard.testing import LoggedInReguestTests


class LocaleChangeTests(LoggedInReguestTests):

    def setUp(self, settings={}):

        super(LocaleChangeTests, self).setUp(settings=settings)
        self.default_language = 'en'

    def test_get_default_lang(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/profile/')
        self.assertIn('<span>{0}</span>'.format(self.default_language),
                      response.body)

    def test_change_language_with_referer(self):
        self.set_logged(user='johnsmith@example.com')
        referer = 'http://localhost/profile/'
        response = self.testapp.get('/set_language/?lang=es',
                                    extra_environ={
                                        'HTTP_REFERER': referer
                                    },
                                    status=302)
        self.assertIsNotNone(response.cookies_set.get('lang', 'es'))
        self.assertEqual(response.location, referer)
        response = self.testapp.get(referer, status=200)
        self.assertIn('<span>es</span>', response.body)

    def test_change_language_without_referer(self):
        self.set_logged(user='johnsmith@example.com')
        response = self.testapp.get('/set_language/?lang=es', status=302)
        self.assertIsNotNone(response.cookies_set.get('lang', 'es'))
        response = self.testapp.get('/profile/', status=200)
        self.assertIn('<span>es</span>', response.body)

    def test_language_cookie(self):
        self.set_logged(user='johnsmith@example.com')
        self.testapp.cookies['lang'] = 'es'
        response = self.testapp.get('/profile/',
                                    status=200)
        self.assertIn('<span>es</span>', response.body)

    def test_change_language_not_available(self):
        self.set_logged(user='johnsmith@example.com')
        self.testapp.get('/set_language/?lang=ph', status=404)
