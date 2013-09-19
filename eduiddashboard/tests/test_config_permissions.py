from eduiddashboard.testing import LoggedInReguestTests


class PermissionsAlternativePemissionsInAdminMode(LoggedInReguestTests):

    formname = 'permissionsview-form'

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': [
            'urn:mace:eduid.se:role:admin',
            'urn:mace:eduid.se:role:manager',
            'urn:mace:eduid.se:role:consultant',
        ],
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': []
    }]

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'admin',
            'available_permissions': """
                urn:mace:eduid.se:role:manager
                urn:mace:eduid.se:role:consultant
                urn:mace:eduid.se:role:student
                urn:mace:eduid.se:role:teacher
                urn:mace:eduid.se:role:helpdesk
            """,
            'permissions_mapping': """
                personal =
                helpdesk = urn:mace:eduid.se:role:helpdesk
                admin = urn:mace:eduid.se:role:manager
            """
        })
        super(PermissionsAlternativePemissionsInAdminMode,
              self).setUp(settings=settings)

    def test_logged_get(self):
        self.set_logged()
        res = self.testapp.get('/users/johnsmith@example.com/permissions/',
                               status=200)
        self.assertIsNotNone(getattr(res, 'form', None))

    def test_notlogged_get(self):
        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=302)

    def test_logged_withoutpermissions_get(self):
        self.set_logged(user='johnsmith@example.org')

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)
