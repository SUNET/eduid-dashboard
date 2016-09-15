from eduiddashboard.testing import LoggedInRequestTests
from eduiddashboard.testing import loa


class LoaTestsAdminMode(LoggedInRequestTests):

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'admin'
        })
        super(LoaTestsAdminMode, self).setUp(settings=settings)

    def test_edit_with_lower_than_the_required_loa(self):
        self.set_logged(
            email ='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(1),
                'eduPersonIdentityProofing': loa(3),
            }
        )

        self.testapp.get('/', status=403)

    def test_edit_with_lower_than_the_required_loa_2(self):
        self.set_logged(
            email ='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(2),
                'eduPersonIdentityProofing': loa(3),
            }
        )

        self.testapp.get('/', status=403)

    def test_edit_with_the_required_loa(self):
        self.set_logged(
            email ='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(3),
                'eduPersonIdentityProofing': loa(3),
            }
        )

        self.testapp.get('/', status=200)

    def test_edit_with_lower_loa(self):
        self.set_logged(
            email ='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(1),
                'eduPersonIdentityProofing': loa(3),
            }
        )

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=403)

    def test_edit_with_required_loa(self):
        self.set_logged(
            email ='johnsmith@example.com',
            extra_session_data={
                'eduPersonAssurance': loa(3),
                'eduPersonIdentityProofing': loa(3),
            }
        )
        self.testapp.get('/users/johnsmith@example.org/permissions/',
                         status=200)


class LoaTestsPersonalMode(LoggedInRequestTests):

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'personal'
        })
        super(LoaTestsPersonalMode, self).setUp(settings=settings)

    def test_edit_with_lower_loa(self):
        self.set_logged(email ='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(1),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/',
                         status=200)

    def test_edit_with_max_loa(self):
        self.set_logged(email ='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(2),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/',
                         status=200)

    def test_edit_with_lower_loa_credentials(self):
        self.set_logged(email ='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(1),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/security/',
                         status=200)  # TODO: revert to 401 when we re-enable step-up auth for security based on AL

    def test_edit_with_max_loa_credentials(self):
        self.set_logged(email ='johnsmith@example.com',
                        extra_session_data={
                            'eduPersonAssurance': loa(2),
                            'eduPersonIdentityProofing': loa(2),
                        })

        self.testapp.get('/profile/security/',
                         status=200)
