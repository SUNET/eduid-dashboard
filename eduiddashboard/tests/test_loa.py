from eduiddashboard.testing import LoggedInReguestTests


class LoaTestsAdminMode(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'maxReachedLoa': 3,
    }, {
        'mail': 'johnsmith@example.org',
        'maxReachedLoa': 1,
    }]

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'admin'
        })
        super(LoaTestsAdminMode, self).setUp(settings=settings)

    def test_edit_with_lower_loa(self):
        self.set_logged(user='johnsmith@example.org',
                        extra_session_data={'loa': 1})

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)

    def test_edit_with_bigger_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'loa': 3})

        self.testapp.get('/users/johnsmith@example.org/permissions/',
                         status=200)

    def test_edit_selfprofile_with_lower_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'loa': 1})

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)

    def test_edit_selfprofile_with_bigger_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'loa': 3})

        self.testapp.get('/users/johnsmith@example.org/permissions/',
                         status=200)


class LoaTestsPersonalMode(LoggedInReguestTests):

    users = [{
        'mail': 'johnsmith@example.com',
        'maxReachedLoa': 3,
    }, {
        'mail': 'johnsmith@example.org',
        'maxReachedLoa': 1,
    }]

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'personal'
        })
        super(LoaTestsPersonalMode, self).setUp(settings=settings)

    def test_edit_with_lower_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'loa': 1})

        self.testapp.get('/profile/',
                         status=200)

    def test_edit_with_bigger_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'loa': 3})

        self.testapp.get('/profile/',
                         status=200)
