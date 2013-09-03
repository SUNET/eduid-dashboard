from eduiddashboard.testing import LoggedInReguestTests


class MailsFormTests(LoggedInReguestTests):

    def test_logged_get(self):
        self.set_logged()
        response = self.testapp.get('/emails/')

        self.assertEqual(response.status, '200 OK')
        self.assertIsNotNone(getattr(response, 'form', None))

    def test_notlogged_get(self):

        response = self.testapp.get('/emails/')
        self.assertEqual(response.status, '302 Found')
