from pyramid.security import (Allow, Deny, Authenticated, Everyone,
                              ALL_PERMISSIONS)

from eduid_am.tasks import update_attributes


class RootFactory(object):
    __acl__ = [
        (Allow, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

    def get_groups(self, userid, request):
        return []


class BaseFactory(object):
    __acl__ = [
        (Allow, Authenticated, ALL_PERMISSIONS),
    ]

    acls = {
        'personal': [
            (Allow, Authenticated, 'edit'),
        ],
        'helpdesk': [
            (Allow, 'helpdesk', 'edit'),
        ],
        'admin': [
            (Allow, 'admin', 'edit'),
        ],
    }

    def __init__(self, request):
        self.request = request
        settings = self.request.registry.settings
        self.workmode = settings.get('workmode')
        self.user = self.get_user()
        self.main_attribute = self.request.registry.settings.get(
            'saml2.user_main_attribute', 'mail')
        self.__acl__ = self.acls[self.workmode]

    def get_user(self):

        if self.workmode == 'personal':
            return self.request.session.get('user', None)
        else:
            userid = self.request.matchdict.get('userid', None)
            if userid:
                return self.request.userdb.get_user(userid)
        return None

    def route_url(self, route, **kw):
        if self.workmode == 'personal':
            return self.request.route_url(route, **kw)
        else:
            userid = self.request.matchdict.get('userid', None)
            return self.request.route_url(route, userid=userid, **kw)

    def update_context_user(self):
        userid = self.user[self.main_attribute]
        self.user = self.request.userdb.get_user(userid)

    def update_session_user(self):
        userid = self.request.session.get('user', {}).get(self.main_attribute,
                                                          None)
        self.user = self.request.userdb.get_user(userid)
        self.request.session['user'] = self.user

    def propagate_user_changes(self, newuser):
        if self.workmode == 'personal':
            self.request.session['user'] = newuser
        else:
            user_session = self.request.session['user'][self.main_attribute]
            if user_session == newuser[self.main_attribute]:
                self.request.session['user'] = newuser

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

    def get_groups(self, userid=None, request=None):
        user = self.request.session.get('user')
        permissions_mapping = self.request.registry.settings.get(
            'permissions_mapping', {})
        required_urn = permissions_mapping.get(self.workmode, '')
        if required_urn is '':
            return ['']
        elif required_urn in user.get('eduPersonEntitlement', []):
            return [self.workmode]
        return []


class PersonFactory(BaseFactory):
    pass


class PasswordsFactory(BaseFactory):
    pass


class PostalAddressFactory(BaseFactory):
    pass


class MobilesFactory(BaseFactory):
    pass


class PermissionsFactory(BaseFactory):
    acls = {
        'personal': [
            (Allow, 'admin', 'edit'),
            (Deny, Authenticated, 'edit'),
        ],
        'helpdesk': [
            (Allow, 'helpdesk', 'edit'),
            (Allow, 'admin', 'edit'),
        ],
        'admin': [
            (Allow, 'admin', 'edit'),
        ],
    }
