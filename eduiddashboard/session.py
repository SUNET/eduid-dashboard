import inspect
import os, binascii
import collections
from time import time
from zope.interface import implementer
from pyramid.interfaces import ISessionFactory, ISession
from eduid_common.session.session import SessionManager
from eduid_userdb.exceptions import UserDoesNotExist
from eduiddashboard.utils import retrieve_modified_ts

import logging
logger = logging.getLogger(__name__)


_EDIT_USER_EPPN = 'edit-user_eppn'
_USER_EPPN = 'user_eppn'


def manage(action):
    '''
    Decorator which causes a cookie to be set when a session method
    is called.

    :param action: Whether the session data has been changed or just accessed.
                   When it has been changed, the call to session.commit()
                   implies setting the ttl on the backend, so there is no need
                   to set it explicitly.
    :type action: str ('accessed'|'changed')
    '''
    def outer(wrapped):
        def accessed(session, *arg, **kw):
            renew_backend = action=='accessed'
            session.renew_ttl(renew_backend=renew_backend)
            return wrapped(session, *arg, **kw)
        accessed.__doc__ = wrapped.__doc__
        return accessed
    return outer


@implementer(ISessionFactory)
class SessionFactory(object):
    '''
    Session factory implementing the pyramid.interfaces.ISessionFactory
    interface.
    It uses the SessionManager defined in eduid_common.session.session
    to create sessions backed by redis.
    '''

    def __init__(self, settings):
        '''
        SessionFactory constructor.

        :param settings: the pyramid settings
        :type settings: dict
        '''
        cookie_max_age = int(settings.get('session.cookie_max_age'))
        # make sure that the data in redis outlives the session cookie
        session_ttl = 2 * cookie_max_age
        secret = settings.get('session.secret')
        self.manager = SessionManager(settings, ttl=session_ttl, secret=secret)

    def __call__(self, request):
        '''
        Create a session object for the given request.

        :param request: the request
        :type request: pyramid.request.Request

        :return: the session
        :rtype: Session
        '''
        self.request = request
        settings = request.registry.settings
        session_name = settings.get('session.key', 'sessid')
        cookies = request.cookies
        token = cookies.get(session_name, None)
        if token is not None:
            base_session = self.manager.get_session(token=token)
            session = Session(request, base_session)
        else:
            base_session = self.manager.get_session(data={})
            base_session['flash_messages'] = {'default': []}
            base_session.commit()
            session = Session(request, base_session, new=True)
            session.set_cookie()
        return session


@implementer(ISession)
class Session(collections.MutableMapping):
    '''
    Session implementing the pyramid.interfaces.ISession interface.
    It uses the Session defined in eduid_common.session.session
    to store the session data in redis.
    '''

    def __init__(self, request, base_session, new=False):
        '''
        :param request: the request
        :type request: pyramid.request.Request
        :param base_session: The underlying session object
        :type base_session: eduid_common.session.session.Session
        :param new: whether the session is new or not.
        :type new: bool
        '''
        self.request = request
        self._session = base_session
        self._created = time()
        self._new = new
        self._ttl_reset = False

    @manage('accessed')
    def __getitem__(self, key, default=None):
        return self._session.__getitem__(key, default=None)

    @manage('changed')
    def __setitem__(self, key, value):
        self._session[key] = value
        self._session.commit()

    @manage('changed')
    def __delitem__(self, key):
        del self._session[key]
        self._session.commit()

    @manage('accessed')
    def __iter__(self):
        return self._session.__iter__()

    @manage('accessed')
    def __len__(self):
        return len(self._session)

    @manage('accessed')
    def __contains__(self, key):
        return self._session.__contains__(key)

    @property
    def created(self):
        '''
        See pyramid.interfaces.ISession
        '''
        return self._created

    @property
    def new(self):
        '''
        See pyramid.interfaces.ISession
        '''
        return self._new

    def invalidate(self):
        '''
        See pyramid.interfaces.ISession
        '''
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
        '''
        See pyramid.interfaces.ISession
        '''
        self._session.commit()

    @manage('changed')
    def flash(self, msg, queue='', allow_duplicate=True):
        '''
        See pyramid.interfaces.ISession
        '''
        if not queue:
            queue = 'default'
        if queue not in self._session['flash_messages']:
            self._session['flash_messages'][queue] = []
        if not allow_duplicate:
            if msg in self._session['flash_messages'][queue]:
                return
        self._session['flash_messages'][queue].append(msg)
        self._session.commit()

    @manage('changed')
    def pop_flash(self, queue=''):
        '''
        See pyramid.interfaces.ISession
        '''
        if not queue:
            queue = 'default'
        if queue in self._session['flash_messages']:
            msgs = self._session['flash_messages'].pop(queue)
            self._session.commit()
            return msgs
        return []

    @manage('accessed')
    def peek_flash(self, queue=''):
        '''
        See pyramid.interfaces.ISession
        '''
        if not queue:
            queue = 'default'
        return self._session['flash_messages'].get(queue, [])

    @manage('changed')
    def new_csrf_token(self):
        '''
        See pyramid.interfaces.ISession
        '''
        token = binascii.hexlify(os.urandom(20))
        self['_csrft_'] = token
        self._session.commit()
        return token

    @manage('accessed')
    def get_csrf_token(self):
        '''
        See pyramid.interfaces.ISession
        '''
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        return token

    def persist(self):
        '''
        Store the session data in the redis backend,
        and renew the ttl for it.
        '''
        self._session.commit()

    def renew_ttl(self, renew_backend):
        '''
        Reset the ttl for the session, both in the cookie and
        (if `renew_backend==True`) in the redis backend.

        :param renew_backend: whether to renew the ttl in the redis backend
        :type renew_backend: bool
        '''
        if not self._ttl_reset:
            self.set_cookie()
            if renew_backend:
                self._session.renew_ttl()
            self._ttl_reset = True

    def set_cookie(self):
        '''
        Set the session cookie with the token
        '''
        token = self._session.token
        settings = self.request.registry.settings
        session_name = settings.get('session.key', 'sessid')
        domain = settings.get('session.cookie_domain')
        path = settings.get('session.cookie_path')
        secure = settings.get('session.cookie_secure')
        httponly = settings.get('session.cookie_httponly')
        max_age = settings.get('session.cookie_max_age')
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
            return True
        self.request.add_response_callback(set_cookie_callback)

    def delete(self):
        '''
        alias for invalidate
        '''
        self.invalidate()


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


def get_session_user(request, legacy_user=False, raise_on_not_logged_in=True):
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
        logger.debug('No logged in user found in session, returning None to {!s}'.format(caller_name()))
        return None
    user = _get_user_by_eppn(request, request.session[_USER_EPPN],
                             legacy_user = legacy_user,
                             )
    try:
        logger.debug('Returning the logged in user {!r} as session user to {!s}'.format(user, caller_name()))
    except IndexError:
        # if the caller is in some template we may get an IndexError
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
    user = request.userdb_new.get_user_by_eppn(eppn)
    retrieve_modified_ts(user, request.dashboard_userdb)
    return user



#
# The function below is intended to aid debugging when we first roll out this
# non-caching of session users. It should probably be removed later, together
# with the rather verbose logging for session user lookups.
#
# -- ft@ 2016-01-15

# From https://gist.github.com/techtonik/2151727
# Public Domain, i.e. feel free to copy/paste
# Considered a hack in Python 2

def caller_name(skip=1):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
      return ''
    name = []
    for i in range(start, len(stack)):
        parentframe = stack[i][0]
        module = inspect.getmodule(parentframe)
        # `modname` can be None when frame is executed directly in console
        # TODO(techtonik): consider using __main__
        if not module:
            break
        if str(module.__name__).upper() == 'EDUIDDASHBOARD.SESSION':
            # We're after the caller of this module, ignore everything *in* this module
            continue
        name.append(module.__name__.upper())
        break
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append( codename ) # function or a method
    del parentframe
    return ".".join(name)
