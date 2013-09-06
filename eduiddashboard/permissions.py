from pyramid.security import (Allow, Authenticated, Everyone,
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
            user = self.request.session.get('user', None)
        else:
            userid = self.request.matchdict.get('userid', None)
            user = self.request.userdb.get_user(userid)
        return user

    def route_url(self, route, **kw):
        if self.workmode == 'personal':
            return self.request.route_url(route, **kw)
        else:
            userid = self.request.matchdict.get('userid', None)
            return self.request.route_url(route, userid=userid, **kw)

    def update_context_user(self):
        userid = self.user[self.main_attribute]
        self.user = self.request.userdb.get_user(userid)

    def propagate_user_changes(self, newuser):
        if self.workmode == 'personal':
            self.request.session['user'] = newuser

        update_attributes.delay('eduid_dashboard', str(self.user['_id']))

    def get_groups(self, userid, request):
        user = self.request.session.get('user')
        permissions_mapping = self.request.registry.settings.get(
            'permission_mapping', {})
        required_urn = permissions_mapping.get(self.workmode, '')
        if required_urn in user.get('eduPersonEntitlement', []):
            return [self.workmode]


class PersonFactory(BaseFactory):
    pass


class PasswordsFactory(BaseFactory):
    pass
