from eduiddashboard.testing import LoggedInReguestTests


class ViewTests(LoggedInReguestTests):

    def test_home_view(self):
        self.set_logged()
        res = self.testapp.get('/')
        self.assertEqual(res.status, '302 Found')
        self.assertEqual('http://localhost/profile/', res.location)
