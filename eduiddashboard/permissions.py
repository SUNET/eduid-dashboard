from pyramid.security import Allow, Authenticated, Everyone, ALL_PERMISSIONS


class RootFactory(object):
    __acl__ = [
        (Allow, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class BaseFactory(object):
    __acl__ = [
        (Allow, Authenticated, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request
        settings = self.request.registry.settings
        self.workmode = settings.get('workmode')
        self.user = self.get_user()
        self.main_attribute = self.request.registry.settings.get(
            'saml2.user_main_attribute', 'mail')

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

    def update_user(self, request):
        userid = self.user[self.main_attribute]
        self.user = self.request.userdb.get_user(userid)


class PersonFactory(BaseFactory):
    pass


class PasswordsFactory(BaseFactory):
    pass
