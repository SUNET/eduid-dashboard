from eduiddashboard.testing import LoggedInReguestTests


class PersonalWorkmodeTests(LoggedInReguestTests):

    def setUp(self, settings={}):
        super(PersonalWorkmodeTests, self).setUp(settings={
            'workmode': 'personal',
        })

    def test_home_view(self):
        self.set_logged()
        res = self.testapp.get('/')
        self.assertEqual(res.status, '302 Found')
        self.assertEqual('http://localhost/profile/', res.location)


class AdminModeTests(LoggedInReguestTests):

    def setUp(self, settings={}):
        super(AdminModeTests, self).setUp(settings={
            'workmode': 'admin',
        })

    def test_home_view(self):
        self.set_logged()
        res = self.testapp.get('/')
        self.assertEqual(res.status, '200 OK')
