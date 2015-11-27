from eduiddashboard.testing import LoggedInRequestTests


class ViewTests(LoggedInRequestTests):

    def test_home_view(self):
        self.set_logged()
        res = self.testapp.get('/')
        self.assertEqual(res.status, '302 Found')
        self.assertEqual('http://localhost/profile/', res.location)

    def test_favicon(self):
        res = self.testapp.get('/favicon.ico')
        self.assertEqual(res.status, '302 Found')