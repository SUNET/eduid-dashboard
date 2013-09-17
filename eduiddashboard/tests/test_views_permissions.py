from eduiddashboard.testing import LoggedInReguestTests


class PermissionsFormTestsAdminMode(LoggedInReguestTests):

    formname = 'permissionsview-form'

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': [
            'urn:mace:eduid.se:role:admin',
        ],
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': []
    }]

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'admin'
        })
        super(PermissionsFormTestsAdminMode, self).setUp(settings=settings)

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

    def test_logged_addpermissions_get(self):
        self.set_logged()
        res = self.testapp.get('/users/johnsmith@example.com/permissions/',
                               status=200)
        self.assertIsNotNone(getattr(res, 'form', None))
        # add any permission
        # change the form
        # query for changed permissions


class PermissionsFormTestsPersonalMode(LoggedInReguestTests):

    formname = 'permissionsview-form'

    users = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': [
            'urn:mace:eduid.se:role:ra',
            'urn:mace:eduid.se:role:admin',
        ],
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': []
    }]

    def setUp(self, settings={}):
        settings.update({
            'workmode': 'personal'
        })
        super(PermissionsFormTestsPersonalMode, self).setUp(settings=settings)

    def test_logged_get(self):
        self.set_logged()
        self.testapp.get('/permissions/', status=404)

    def test_notlogged_get(self):
        self.testapp.get('/permissions/', status=404)
