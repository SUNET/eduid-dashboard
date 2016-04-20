from bson import ObjectId
from eduiddashboard.testing import LoggedInRequestTests


class PermissionsFormTestsAdminMode(LoggedInRequestTests):

    formname = 'permissionsview-form'

    # Patch some parts of the mock users in eduid_userdb.testing.MongoTestCase
    mock_users_patches = [{
        'mail': 'johnsmith@example.com',
        'eduPersonEntitlement': [
            'urn:mace:eduid.se:role:admin',
        ],
    }, {
        'mail': 'johnsmith@example.org',
        'eduPersonEntitlement': []
    }]

    def setUp(self, settings={}):
        # Make sure the default permission mappings are set here - the mappings
        # are changed in test_config_permissions.py and that affects this test too :( :(
        settings.update({
            'workmode': 'admin',
            'available_permissions': """
urn:mace:eduid.se:role:ra
urn:mace:eduid.se:role:admin
urn:mace:eduid.se:role:manager
urn:mace:eduid.se:role:consultant
urn:mace:eduid.se:role:student
urn:mace:eduid.se:role:teacher
urn:mace:eduid.se:role:helpdesk
            """,
            'permissions_mapping': """
personal =
helpdesk = urn:mace:eduid.se:role:ra
admin = urn:mace:eduid.se:role:admin
            """
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
        self.set_logged(email ='johnsmith@example.org')

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)

    def test_logged_addpermissions(self):
        self.set_logged()
        res = self.testapp.get('/users/johnsmith@example.org/permissions/',
                               status=200)
        self.assertIsNotNone(getattr(res, 'form', None))

        self.check_values(res.form.fields.get('checkbox'),
                          ['urn:mace:eduid.se:role:admin'])

        res = res.form.submit('save')

        user = self.dashboard_db.get_user_by_id(ObjectId('901234567890123456789012'))

        self.assertEqual(user.entitlements, ['urn:mace:eduid.se:role:admin'])

    def test_logged_remove_admin_permissions(self):
        self.set_logged(email ='johnsmith@example.com')
        res = self.testapp.get('/users/johnsmith@example.org/permissions/',
                               status=200)
        self.assertIsNotNone(getattr(res, 'form', None))

        self.check_values(res.form.fields.get('checkbox'),
                          ['urn:mace:eduid.se:role:ra'])

        res = res.form.submit('save')

        user = self.userdb_new.get_user_by_id(ObjectId('901234567890123456789012'))

        self.assertEqual(user.entitlements, ['urn:mace:eduid.se:role:ra'])

        self.set_logged(email ='johnsmith@example.org')

        self.testapp.get('/users/johnsmith@example.com/permissions/',
                         status=401)

    def test_logged_add_dirty_permissions(self):
        self.set_logged()
        res = self.testapp.get('/users/johnsmith@example.org/permissions/',
                               status=200)
        self.assertIsNotNone(getattr(res, 'form', None))

        self.check_values(res.form.fields.get('checkbox'),
                          ['urn:mace:eduid.se:role:admin', 'dirty-permissions'],
                          ignore_not_found = ['dirty-permissions']
                          )

        res = res.form.submit('save')

        user = self.userdb_new.get_user_by_id(ObjectId('901234567890123456789012'))

        self.assertEqual(user.entitlements, ['urn:mace:eduid.se:role:admin'])


class PermissionsFormTestsPersonalMode(LoggedInRequestTests):

    formname = 'permissionsview-form'

    mock_users_patches = [{
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
