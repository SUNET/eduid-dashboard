import re

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden, HTTPFound
from pyramid.settings import asbool
from pyramid.security import (Allow, Deny, Authenticated, Everyone,
                              ALL_PERMISSIONS)
from pyramid.security import forget, authenticated_userid
from eduiddashboard.i18n import TranslationString as _

from eduid_am.tasks import update_attributes
from eduid_am.user import User

import logging
logger = logging.getLogger(__name__)

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

    def propagate_user_changes(self, user):
        update_attributes.delay('eduid_dashboard', str(user['_id']))


def is_logged(request):
    user = authenticated_userid(request)
    if user is None:
        return False
    if request.session.get('user', None) is None:
        return False
    return True


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

    user = None

    def __init__(self, request):
        try:
            user = request.session.get('user')
        except OSError:
            # If any of the beaker session files is removed, then
            # a OSError is raised, so we want to relogin the user
            user = None

        if user is None:
            headers = forget(request)
            url = request.route_path('saml2-login')
            home = request.route_path('home')
            url += '?next={0}'.format(home)
            raise HTTPFound(location=url, headers=headers)
        self.request = request
        settings = self.request.registry.settings
        self.workmode = settings.get('workmode')
        self.user = self.get_user()
        self.main_attribute = self.request.registry.settings.get(
            'saml2.user_main_attribute', 'mail')

        if not self.authorize():
            logger.debug('Un-authorized access attempt to user {!r}'.format(self.user))
            raise HTTPForbidden(_('You do not have sufficient permissions to access this user'))

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
        #         raise HTTPForbidden(_('You do not have sufficient AL to edit this user'))

        required_loa = self.request.registry.settings.get('required_loa', {})
        required_loa = required_loa.get(self.workmode, '')

        user_loa_int = self.loa_to_int()
        required_loa_int = self.loa_to_int(loa=required_loa)

        if user_loa_int < required_loa_int:
            logger.info('User AL too low for workmode {!r} ({!r} < {!r})'.format(
                self.workmode, self.get_loa(), required_loa))
            raise HTTPForbidden(_('You do not have sufficient AL to access to this '
                                'workmode'))

        return True

    def get_user(self):

        # Cache user until the request is completed
        if self.user is not None:
            return self.user

        user = None
        if self.workmode == 'personal':
            user = self.request.session.get('user', User({}))
        else:
            user = self.request.session.get('edit-user', None)
            if user is None:
                userid = self.request.matchdict.get('userid', '')
                if EMAIL_RE.match(userid):
                    user = self.request.userdb.get_user(userid)
                elif OID_RE.match(userid):
                    user = self.request.userdb.get_user_by_oid(userid)
                if not user:
                    raise HTTPNotFound()
                user.retrieve_modified_ts(self.request.db.profiles)
                self.request.session['edit-user'] = user
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
            userid = self.user.get_id()
            return self.request.route_url(route, userid=userid, **kw)

    def update_context_user(self):
        userid = self.user.get(self.main_attribute)
        self.user = self.request.userdb.get_user(userid)
        self.user.retrieve_modified_ts(self.request.db.profiles)

    def update_session_user(self):
        user = self.request.session.get('user', User({}))
        userid = user.get(self.main_attribute, None)
        user = self.request.userdb.get_user(userid)
        self.user = user
        self.user.retrieve_modified_ts(self.request.db.profiles)
        if self.workmode == 'personal':
            self.request.session['user'] = user
        else:
            self.request.session['edit-user'] = user

    def propagate_user_changes(self, newuser):
        if self.workmode == 'personal':
            # Only update session if user is the same as currently in session
            user = self.request.session.get('user')
            newuser = User(newuser)
            if user.get_id() == newuser.get_id():
                self.request.session['user'] = newuser
        else:
            user_session = self.request.session['user'].get(self.main_attribute)
            if user_session == newuser[self.main_attribute]:
                newuser = User(newuser)
                self.request.session['edit-user'] = newuser

        update_attributes.delay('eduid_dashboard', str(newuser['_id']))

    def get_groups(self, userid=None, request=None):
        user = self.request.session.get('user', User({}))
        permissions_mapping = self.request.registry.settings.get(
            'permissions_mapping', {})
        required_urn = permissions_mapping.get(self.workmode, '')
        if required_urn is '':
            return ['']
        elif required_urn in user.get_entitlements():
            return [self.workmode]
        return []

    def get_loa(self):
        available_loa = self.request.registry.settings.get('available_loa')
        return self.request.session.get('eduPersonAssurance', available_loa[0])

    def get_max_loa(self):
        max_loa = self.request.session.get('eduPersonIdentityProofing', None)
        if max_loa is None:
            max_loa = self.request.userdb.get_identity_proofing(
                self.request.session.get('user', User({})))
            self.request.session['eduPersonIdentityProofing'] = max_loa

        return max_loa

    def loa_to_int(self, loa=None):
        available_loa = self.request.registry.settings.get('available_loa')

        if loa is None:
            loa = self.get_loa()
        try:
            return available_loa.index(loa) + 1
        except ValueError:
            return 1

    def session_user_display(self):
        user = self.request.session.get('user', User({}))
        display_name = user.get_display_name()
        if display_name:
            return display_name

        gn = user.get_given_name()
        sn = user.get_sn()
        if gn and sn:
            return "{0} {1}".format(gn, sn)

        return user.get_mail()

    def get_preferred_language(self):
        """ Return always a """
        lang = self.user.get_preferred_language()
        if lang is not None:
            return lang
        available_languages = self.request.registry.settings.get('available_languages', {}).keys()
        if len(available_languages) > 0:
            return available_languages[0]
        else:
            return 'en'


class ForbiddenFactory(RootFactory):
    __acl__ = [
        (Deny, Everyone, ALL_PERMISSIONS),
    ]


class BaseCredentialsFactory(BaseFactory):

    def authorize(self):
        if self.request.session.get('user') is None:
            raise HTTPForbidden(_('Not logged in'))
        is_authorized = super(BaseCredentialsFactory, self).authorize()

        # Verify that session loa is equal than the max reached
        # loa
        max_user_loa = self.get_max_loa()
        session_loa = self.get_loa()

        if session_loa != max_user_loa:
            raise HTTPForbidden(_('You must be logged in with {user_AL} '
                                  'to manage your credentials',
                                  mapping={'user_AL': max_user_loa}))
        return is_authorized


class HomeFactory(BaseFactory):

    def get_user(self):
        return self.request.session.get('user', User({}))


class HelpFactory(BaseFactory):
    pass


class PersonFactory(BaseFactory):
    pass


class SecurityFactory(BaseFactory):
    # TODO: Revert to BaseCredentialsFactory after refactoring the AL implementation
    pass


class PostalAddressFactory(BaseFactory):
    pass


class MobilesFactory(BaseFactory):
    pass


class NinsFactory(BaseFactory):
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
        user = self.request.userdb.get_user_by_oid(verification_code['user_oid'])
        user.retrieve_modified_ts(self.request.db.profiles)
        return user


class StatusFactory(BaseFactory):
    pass


class ProofingFactory(BaseFactory):
    pass


class AdminFactory(BaseFactory):
    pass
