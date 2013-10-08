import re

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden
from pyramid.settings import asbool
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

        if not self.authorize():
            raise HTTPForbidden('You have not sufficient permissions to access this user')

        self.__acl__ = self.acls[self.workmode]

    def authorize(self):
        """You must overwrite this method is you want to get another
           authorization access method no based in the ACLs.
           If you want to unauthorized the acces to this resource you must
           raise a HTTPForbidden exception
        """

        ### This block enable the requirent of the user must have more loa
        # # that the loa from edited user
        # if self.user is not None:
        #     # Verify that session loa is iqual or bigger than the edited user
        #     max_user_loa = self.get_max_loa()
        #     max_user_loa = self.loa_to_int(loa=max_user_loa)
        #     session_loa = self.loa_to_int()
        #     if session_loa < max_user_loa:
        #         raise HTTPForbidden('You have not sufficient AL to edit this user')

        required_loa = self.request.registry.settings.get('required_loa', {})
        required_loa = required_loa.get(self.workmode, '')

        user_loa_int = self.loa_to_int()
        required_loa_int = self.loa_to_int(loa=required_loa)

        if user_loa_int < required_loa_int:
            raise HTTPForbidden('You have not sufficient AL to access to this '
                                'workmode')

        return True

    def get_user(self):

        # Cache user until the request is completed
        if self._user is not None:
            return self._user

        user = None
        if self.workmode == 'personal':
            user = self.request.session.get('user', None)
            userid = user and user.get('mail', '') or ''
        else:
            userid = self.request.matchdict.get('userid', '')
        cache_user_in_session = asbool(self.request.registry.settings.get(
            'cache_user_in_session', True))
        if not cache_user_in_session or self.workmode != 'personal':
            if EMAIL_RE.match(userid):
                user = self.request.userdb.get_user(userid)
            elif OID_RE.match(userid):
                user = self.request.userdb.get_user_by_oid(userid)
            if not user:
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
            app_url = self.request.registry.settings.get(
                'personal_dashboard_base_url', None)
            if app_url:
                kw['_app_url'] = app_url
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

        update_attributes.delay('eduid_dashboard', str(newuser['_id']))

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

    def get_loa(self):
        available_loa = self.request.registry.settings.get('available_loa')
        return self.request.session.get('eduPersonAssurance',
                                        available_loa[0])

    def get_max_loa(self):
        available_loa = self.request.registry.settings.get('available_loa')
        return self.request.session.get('eduPersonIdentityProofing',
                                        available_loa[0])

    def loa_to_int(self, loa=None):
        available_loa = self.request.registry.settings.get('available_loa')

        if loa is None:
            loa = self.get_loa()
        try:
            return available_loa.index(loa) + 1
        except ValueError:
            return 1


class ForbiddenFactory(RootFactory):
    __acl__ = [
        (Deny, Everyone, ALL_PERMISSIONS),
    ]


class BaseCredentialsFactory(BaseFactory):

    def authorize(self):
        is_authorized = super(BaseCredentialsFactory, self).authorize()

        # Verify that session loa is equal than the max reached
        # loa
        max_user_loa = self.get_max_loa()
        session_loa = self.get_loa()

        if session_loa != max_user_loa:
            raise HTTPForbidden('You have not sufficient AL to edit your'
                                ' credentials')
        return is_authorized


class HomeFactory(BaseFactory):

    def get_user(self):
        return self.request.session.get('user', None)


class PersonFactory(BaseFactory):
    pass


class PasswordsFactory(BaseCredentialsFactory):
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

    def get_user(self):
        verification_code = self.request.db.verifications.find_one({
            'code': self.request.matchdict['code'],
        })
        if verification_code is None:
            raise HTTPNotFound()
        return self.request.userdb.get_user_by_oid(verification_code['user_oid'])



class StatusFactory(BaseFactory):
    pass
