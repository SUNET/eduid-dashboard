import re

from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden, HTTPFound
from pyramid.security import (Allow, Deny, Authenticated, Everyone,
                              ALL_PERMISSIONS)
from pyramid.security import forget, authenticated_userid
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.utils import retrieve_modified_ts
from eduiddashboard.session import (get_session_user, get_logged_in_user,
                                    has_logged_in_user, has_edit_user,
                                    store_session_user)

from eduid_userdb.dashboard import DashboardUser
from eduid_userdb import User

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
        """
        Use Celery to ask eduid-am worker to propagate changes from our
        private DashboardUserDB into the central UserDB.

        :param user: User object

        :type user: DasboardLegacyUser or DashboardUser
        :return:
        """
        logger.debug('Root factory propagate_user_changes')
        return self.request.amrelay.request_sync(user)

    def save_dashboard_user(self, user):
        """
        Save (new) user objects to the dashboard db in the new format,
        and propagate the changes to the central user db.

        May raise UserOutOfSync exception

        :param user: the modified user
        :type user: eduid_userdb.dashboard.user.DashboardUser
        """
        if isinstance(user, User):
            # turn it into a DashboardUser before saving it in the dashboard private db
            user = DashboardUser(data = user.to_dict())
        self.request.dashboard_userdb.save(user, old_format=False)
        self.propagate_user_changes(user)


def is_logged(request):
    user = authenticated_userid(request)
    if user is None:
        return False
    return has_logged_in_user(request)


class BaseFactory(RootFactory):
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

    #user = None

    def __init__(self, request):
        user = get_logged_in_user(request, legacy_user = False, raise_on_not_logged_in = False)
        self._logged_in_user = user
        self.request = request
        settings = self.request.registry.settings
        self.workmode = settings.get('workmode')
        self.main_attribute = 'eduPersonPrincipalName'
        self._cached_user = None

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

    @property
    def user(self):
        """
        Get the 'current user', as returned by get_user().

        This user object is cached typically in what is known as the 'context'
        around the dashboard. The context is ephemeral to each processed request.
        :return: The current user
        :rtype: DashboardLegacyUser
        """
        if self._cached_user is None:
            self._cached_user = self.get_user()
        return self._cached_user

    def get_user(self):
        """
        Get the current user.

        In 'personal' mode, this is the logged in user. In 'admin' mode, it is the
        'edit-user' user from the session, or the user indicated by the matchdict
        'userid'. Matchdict is a part of the URL extracted by Pyramid with routes like
        '/users/{userid}/'.

        :return: User object
        :rtype: DashboardUser
        """
        if self.workmode == 'personal':
            user = get_logged_in_user(self.request, legacy_user = False, raise_on_not_logged_in = False)
            self._logged_in_user = user
        elif self.workmode == 'admin' or self.workmode == 'helpdesk':
            if not has_edit_user(self.request):
                user = None
                userid = self.request.matchdict.get('userid', '')
                logger.debug('get_user() looking for user matching {!r}'.format(userid))
                if EMAIL_RE.match(userid):
                    user = self.request.userdb_new.get_user_by_mail(userid)
                elif OID_RE.match(userid):
                    user = self.request.userdb_new.get_user_by_id(userid)
                if not user:
                    raise HTTPNotFound()
                logger.debug('get_user() storing user {!r}'.format(user))
                store_session_user(self.request, user, edit_user = True)
            user = get_session_user(self.request)
        else:
            raise NotImplementedError("Unknown workmode: {!s}".format(self.workmode))

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
            userid = self.user.user_id
            return self.request.route_url(route, userid=userid, **kw)

    def update_context_user(self):
        # XXX what is this context user???
        logger.notice('UPDATE CONTEXT USER CALLED')
        raise NotImplementedError('update_context_user UN-implemented')
        eppn = self.user.eppn
        self.user = self.request.userdb_new.get_user_by_eppn(eppn)
        retrieve_modified_ts(self.user, self.request.dashboard_userdb)

    def get_groups(self, userid=None, request=None):
        #user = get_logged_in_user(self.request, legacy_user = True, raise_on_not_logged_in = False)
        user = self._logged_in_user
        permissions_mapping = self.request.registry.settings.get(
            'permissions_mapping', {})
        required_urn = permissions_mapping.get(self.workmode, '')
        if required_urn is '':
            return ['']
        if required_urn in user.entitlements:
            return [self.workmode]
        logger.debug("Required URN {!r} not found in user {!r} entitlements: {!r}".format(
            required_urn, user, user.entitlements))
        return []

    def get_loa(self):
        available_loa = self.request.registry.settings.get('available_loa')
        return self.request.session.get('eduPersonAssurance', available_loa[0])

    def get_max_loa(self):
        max_loa = self.request.session.get('eduPersonIdentityProofing', None)
        if max_loa is None:
            user = self.get_user()
            max_loa = self.request.userdb_new.get_identity_proofing(user)
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
        user = self.get_user()
        display_name = user.display_name
        if display_name:
            return display_name

        gn = user.given_name
        sn = user.surname
        if gn and sn:
            return "{0} {1}".format(gn, sn)

        if user.mail_addresses.primary is not None:
            return user.mail_addresses.primary.email
        return user.eppn

    def get_preferred_language(self):
        """ Return always a """
        lang = self.get_user().language
        if lang is not None:
            return lang
        available_languages = self.request.registry.settings.get('available_languages', {}).keys()
        if len(available_languages) > 0:
            return available_languages[0]
        else:
            return 'en'

    def get_js_bundle_name(self):
        """
        Select the name of the js bundle with react components
        that will be used during the session.
        There is a default bundle,
        and we can configure different bundles for specific users.
        Also, we can set up A/B testing, configuring the percentages
        of the requests that each of the bundles under test will
        be selected.

        :return: the bundle to be used in this session
        :rtype: str
        """
        bundle = self.request.session.get('js_bundle', '')
        if not bundle:
            user = self.get_user()
            email = user.mail_addresses.primary.email

            settings = self.request.registry.settings
            bundle = settings.get('js_bundle_default')
            config_people = settings.get('js_bundle_people', None)
            config_ab = settings.get('js_bundle_abtesting', None)

            if config_people and email in config_people.keys():
                bundle = config_people[email]

            elif config_ab:
                user_percent = ( ord(user.eppn[0]) - ord('a') ) *  4
                accum = 0
                for percent, bundle in config_ab.items():
                    accum += int(percent)
                    if user_percent < accum:
                        break

            self.request.session['js_bundle'] =  bundle

        return bundle


class ForbiddenFactory(RootFactory):
    __acl__ = [
        (Deny, Everyone, ALL_PERMISSIONS),
    ]


class BaseCredentialsFactory(BaseFactory):

    def authorize(self):
        if not has_logged_in_user(self.request):
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
        # XXX what's the purpose here? Override BaseFactory.get_user() to never get edit-user?
        user = get_logged_in_user(self.request, legacy_user = False, raise_on_not_logged_in = False)
        logger.debug('HomeFactory get_user returning {!s}'.format(user))
        return user


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
        logger.debug("Looking for verification code {!r}".format(self.request.matchdict['code']))
        verification_code = self.request.db.verifications.find_one({
            'code': self.request.matchdict['code'],
        })
        if verification_code is None:
            raise HTTPNotFound()
        user = self.request.userdb_new.get_user_by_id(verification_code['user_oid'])
        retrieve_modified_ts(user, self.request.dashboard_userdb)
        return user


class StatusFactory(BaseFactory):
    pass


class ProofingFactory(BaseFactory):
    pass


class AdminFactory(BaseFactory):
    pass
