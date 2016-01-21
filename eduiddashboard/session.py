
import os, binascii
from time import time
import collections
from zope.interface import implementer
from pyramid.interfaces import ISessionFactory, ISession
from eduid_common.session.session import SessionManager

import logging
logger = logging.getLogger(__name__)


_EDIT_USER_EPPN = 'edit-user_eppn'
_USER_EPPN = 'user_eppn'


@implementer(ISessionFactory)
class SessionFactory(object):

    def __init__(self, settings):
        redis_host = settings['redis_host']
        redis_port = settings['redis_port']
        redis_db = settings['redis_db']
        self.manager = SessionManager(redis_host, redis_port, redis_db)

    def __call__(self, request):
        self.request = request
        settings = request.registry.settings
        session_name = settings.get('session.key', 'sessid')
        secret = settings.get('session.secret')
        cookies = request.cookies
        token = cookies.get(session_name, None)
        if token is not None:
            base_session = self.manager.get_session(token=token, secret=secret)
            new = False
        else:
            base_session = self.manager.get_session(data={}, secret=secret)
            base_session['flash_messages'] = {'default': []}
            base_session.commit()
            token = base_session.token
            domain = settings.get('session.cookie_domain')
            path = settings.get('session.cookie_path')
            secure = settings.get('session.cookie_secure')
            httponly = settings.get('session.cookie_httponly')
            max_age = settings.get('session.cookie_max_age')
            new = True
            def set_cookie_callback(request, response):
                response.set_cookie(
                        name=session_name,
                        value=token,
                        domain=domain,
                        path=path,
                        secure=secure,
                        httponly=httponly,
                        max_age=max_age
                        )
                self.request = None
                return True
            self.request.add_response_callback(set_cookie_callback)
        return Session(request, base_session, new)


@implementer(ISession)
class Session(collections.MutableMapping):

    _dirty = False

    def __init__(self, request, base_session, new):
        self.request = request
        self._session = base_session
        self._created = time()
        self._new = new
        self._changed = False

    def __getitem__(self, key, default=None):
        return self._session.__getitem__(key, default=None)

    def __setitem__(self, key, value):
        self._session[key] = value
        self._session.commit()

    def __delitem__(self, key):
        del self._session[key]
        self._session.commit()

    def __iter__(self):
        return self._session.__iter__()

    def __len__(self):
        return len(self._session)

    def __contains__(self, key):
        return self._session.__contains__(key)

    @property
    def created(self):
        return self._created

    @property
    def new(self):
        return self._new

    def invalidate(self):
        self._session.clear()
        name = self.request.registry.settings.get('session.key')
        domain = self.request.registry.settings.get('session.cookie_domain')
        path = self.request.registry.settings.get('session.cookie_path')
        def rm_cookie_callback(request, response):
            response.set_cookie(
                    name=name,
                    value=None,
                    domain=domain,
                    path=path,
                    max_age=0
                    )
            return True
        self.request.add_response_callback(rm_cookie_callback)

    def changed(self):
        self._session.commit()

    def flash(self, msg, queue='', allow_duplicate=True):
        if not queue:
            queue = 'default'
        elif queue not in self._session['flash_messages']:
            self._session['flash_messages'][queue] = []
        if not allow_duplicate:
            if msg in self._session['flash_messages'][queue]:
                return
        self._session['flash_messages'][queue].append(msg)
        self._session.commit()

    def pop_flash(self, queue=''):
        if not queue:
            queue = 'default'
        if queue in self._session['flash_messages']:
            msgs = self._session['flash_messages'].pop(queue)
            self._session.commit()
            return msgs
        return []

    def peek_flash(self, queue=''):
        if not queue:
            queue = 'default'
        return self._session['flash_messages'].get(queue, [])

    def new_csrf_token(self):
        token = binascii.hexlify(os.urandom(20))
        self['_csrft_'] = token
        self._session.commit()
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        return token

    def persist(self):
        self._session.commit()



def store_session_user(request, user, edit_user=False):
    """
    Set currently logged in/session user.

    If edit_user = True, this will update which user is returned by get_session_user,
    but not the user returned by get_logged_in_user.

    :param request: Pyramid request object
    :param user: New user to store in session
    :param edit_user: If True update session_user, not logged_in_user

    :type user: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    :type edit_user: bool
    :return:
    """
    try:
        eppn = user.eppn
    except AttributeError:
        eppn = user.get_eppn()
    if edit_user:
        request.session[_EDIT_USER_EPPN] = eppn
    else:
        request.session[_USER_EPPN] = eppn
    logger.debug('Stored user {!r} eppn in session (edit-user: {!s})'.format(user, edit_user))


def has_edit_user(request):
    """
    Check if there is an 'edit-user' in the session.

    Used when initializing helpdesk/admin mode - if there is no 'edit-user' in the session
    some request parameters are parsed and an edit-user is stored.

    :param request: Pyramid request object
    :return: True if an edit-user has been stored in the session
    :rtype: bool
    """
    return _EDIT_USER_EPPN in request.session


def has_logged_in_user(request):
    """
    Check if there is a logged in user in the session.

    :param request: Pyramid request object
    :return: True if a logged in user has been stored in the session
    :rtype: bool
    """
    return _USER_EPPN in request.session


def get_session_user(request, legacy_user, raise_on_not_logged_in=True):
    """
    Get the session user. This is the user being worked on, in helpdesk mode
    it is not necessarily the currently logged in user. See get_logged_in_user().

    :param request: Pyramid request object
    :param legacy_user: Request a DashboardLegacyUser and not a User
    :param raise_on_not_logged_in: Treat absense of a user in the session as an error

    :return: The session user
    :rtype: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    """
    if _EDIT_USER_EPPN in request.session:
        user = _get_user_by_eppn(request, request.session[_EDIT_USER_EPPN],
                                 legacy_user = legacy_user,
                                 )
        logger.debug('Returning the edit-user {!r} as session user'.format(user))
    else:
        user = get_logged_in_user(request,
                                  legacy_user = legacy_user,
                                  raise_on_not_logged_in = raise_on_not_logged_in)
    return user


def get_logged_in_user(request, legacy_user, raise_on_not_logged_in=True):
    """
    Get the currently logged in user.

    :param request: Pyramid request object
    :param legacy_user: Request a DashboardLegacyUser and not a User
    :param raise_on_not_logged_in: Treat absense of a user in the session as an error

    :return: The logged in user
    :rtype: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    """
    if not raise_on_not_logged_in and _USER_EPPN not in request.session:
        logger.debug('No logged in user found in session, returning None')
        return None
    user = _get_user_by_eppn(request, request.session[_USER_EPPN],
                             legacy_user = legacy_user,
                             )
    logger.debug('Returning the logged in user {!r} as session user'.format(user))
    return user


def _get_user_by_eppn(request, eppn, legacy_user):
    """
    Fetch a user in either legacy format or the new eduid_userdb.User format.

    :param request: Pyramid request object
    :param eppn: eduPersonPrincipalName
    :param legacy_user: Use old format or not

    :type eppn: str | unicode
    :type legacy_user: bool

    :return: DashboardUser
    :rtype: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    """
    if legacy_user:
        user = request.userdb.get_user_by_eppn(eppn)
        logger.debug('Loading modified_ts from dashboard db (profiles) for user {!r}'.format(user))
        user.retrieve_modified_ts(request.db.profiles)
        return user
    return request.userdb_new.get_user_by_eppn(eppn)
