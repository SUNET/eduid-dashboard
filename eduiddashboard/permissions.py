import re

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden

from pyramid.security import (Allow, Deny, Authenticated, Everyone,
                              ALL_PERMISSIONS)

from eduid_am.tasks import update_attributes


EMAIL_RE = re.compile(r'[^@]+@[^@]+')
OID_RE = re.compile(r'[0-9a-fA-F]{12}')


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

    _user = None

    def __init__(self, request):
        self.request = request
        settings = self.request.registry.settings
        self.workmode = settings.get('workmode')
        self.user = self.get_user()
        self.main_attribute = self.request.registry.settings.get(
            'saml2.user_main_attribute', 'mail')
        if self.user is not None:
            # Verify that session loa is iqual or bigger than the edited user
            max_user_loa = self.user.get('maxReachedLoa', 1)
            session_loa = self.request.session.get('loa', 1)

            if session_loa < max_user_loa:
                raise HTTPForbidden('You have not sufficient AL to edit this user')

        self.__acl__ = self.acls[self.workmode]

    def get_user(self):

        # Cache user until the request is completed
        if self._user is not None:
            return self._user

        user = None
        if self.workmode == 'personal':
            user = self.request.session.get('user', None)
        else:
            userid = self.request.matchdict.get('userid', '')
            if EMAIL_RE.match(userid):
                user = self.request.userdb.get_user(userid)
            elif OID_RE.match(userid):
                user = self.request.userdb.get_user_by_oid(userid)
            if not user and userid:
                raise HTTPNotFound()
        self._user = user
        return user

    def route_url(self, route, **kw):
        if self.workmode == 'personal':
            return self.request.route_url(route, **kw)
        else:
            userid = self.request.matchdict.get('userid', None)
            return self.request.route_url(route, userid=userid, **kw)

    def safe_route_url(self, route, **kw):
        if self.workmode == 'personal':
            return self.request.route_url(route, **kw)
        else:
            userid = self.user['_id']
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


class ResetPasswordFactory(RootFactory):
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


class VerificationsFactory(BaseFactory):
    pass


class StatusFactory(BaseFactory):
    pass


class ProofingFactory(BaseFactory):
    pass
