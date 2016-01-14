import logging
log = logging.getLogger(__name__)


_EDIT_USER_EPPN = 'edit-user_eppn'
_USER_EPPN = 'user_eppn'


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
    log.debug('Stored user {!r} eppn in session (edit-user: {!s})'.format(user, edit_user))


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
        log.debug('Returning the edit-user {!r} as session user'.format(user))
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
        log.debug('No logged in user found in session, returning None')
        return None
    user = _get_user_by_eppn(request, request.session[_USER_EPPN],
                             legacy_user = legacy_user,
                             )
    log.debug('Returning the logged in user {!r} as session user'.format(user))
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
        log.debug('Loading modified_ts from dashboard db (profiles) for user {!r}'.format(user))
        user.retrieve_modified_ts(request.db.profiles)
        return user
    return request.userdb_new.get_user_by_eppn(eppn)
