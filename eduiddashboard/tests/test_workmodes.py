from eduiddashboard.testing import LoggedInReguestTests


class PersonalWorkmodeTests(LoggedInReguestTests):

    def setUp(self, settings={}):
        super(PersonalWorkmodeTests, self).setUp(settings={
            'workmode': 'personal',
        })

    def test_home_view(self):
        self.set_logged()
        res = self.testapp.get('/', status=302)
        self.assertEqual('http://localhost/profile/', res.location)

    def test_profile_view(self):
        self.set_logged()
        self.testapp.get('/profile/', status=200)

    def test_profile_view_form(self):
        self.set_logged()
        self.testapp.get('/profile/emails/', status=200)

    def test_otheruser_profile_view(self):
        self.set_logged()
        self.testapp.get('/users/johnsmith@example.com/', status=404)

    def test_otheruser_profile_view_form(self):
        self.set_logged()
        self.testapp.get('/users/johnsmith@example.com/emails/', status=404)


class AdminModeTests(LoggedInReguestTests):

    def setUp(self, settings={}):
        super(AdminModeTests, self).setUp(settings={
            'workmode': 'admin',
        })

    def test_home_view(self):
        self.set_logged()
        self.testapp.get('/', status=200)

    def test_profile_view(self):
        self.set_logged()
        self.testapp.get('/profile/', status=404)

    def test_profile_view_form(self):
        self.set_logged()
        self.testapp.get('/profile/emails/', status=404)

    def test_otheruser_profile_view(self):
        self.set_mocked_get_user()
        self.set_logged()
        self.testapp.get('/users/johnsmith@example.com/', status=200)

    def test_otheruser_profile_view_form(self):
        self.set_mocked_get_user()
        self.set_logged()
        self.testapp.get('/users/johnsmith@example.com/emails/', status=200)
