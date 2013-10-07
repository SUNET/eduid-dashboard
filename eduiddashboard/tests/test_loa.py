from eduiddashboard.testing import LoggedInReguestTests, loa


class LoaTestsAdminMode(LoggedInReguestTests):

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'admin'
        })
        super(LoaTestsAdminMode, self).setUp(settings=settings)

    def test_edit_with_lower_loa(self):
        self.set_logged(
            user='johnsmith@example.org',
            extra_session_data={
                'eduPersonAssurance': loa(1),
                'eduPersonIdentityProofing': loa(2),
            }
        )

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)

    def test_edit_with_bigger_loa(self):
        self.set_logged(
            user='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(3),
                'eduPersonIdentityProofing': loa(3),
            }
        )
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={'eduPersonAssurance': loa(3)})

        self.testapp.get('/users/johnsmith@example.org/passwords/',
                         status=200)

    def test_edit_selfprofile_with_lower_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(2),
                            'eduPersonIdentityProofing': loa(3),
                        })

        self.testapp.get('/users/johnsmith@example.com/passwords/',
                         status=401)

    def test_edit_selfprofile_with_bigger_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(3),
                            'eduPersonIdentityProofing': loa(3),
                        })

        self.testapp.get('/users/johnsmith@example.org/passwords/',
                         status=200)


class LoaTestsPersonalMode(LoggedInReguestTests):

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'personal'
        })
        super(LoaTestsPersonalMode, self).setUp(settings=settings)

    def test_edit_with_lower_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(1),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/',
                         status=200)

    def test_edit_with_max_loa(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(2),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/',
                         status=200)

    def test_edit_with_lower_loa_credentials(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(1),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/passwords/',
                         status=401)

    def test_edit_with_max_loa_credentials(self):
        self.set_logged(user='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(2),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/passwords/',
                         status=200)
