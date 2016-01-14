_EDIT_USER = 'edit-user'
_USER = 'user'


def store_session_user(request, user, edit_user=False):
    """
    Set currently logged in/session user.

    If edit_user = True, this will update which user is returned by get_session_user,
    but not the user returned by get_logged_in_user.

    :param request: Pyramid request object
    :param user: New user
    :param edit_user: If True update session_user, not logged_in_user

    :type user: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    :type edit_user: bool
    :return:
    """
    if edit_user:
        request.session[_EDIT_USER] = user
    else:
        request.session[_USER] = user


def get_session_user(request, legacy_user=False, raise_on_not_logged_in=True):
    """
    Get the session user. This is the user being worked on, in helpdesk mode
    it is not necessarily the currently logged in user. See get_logged_in_user().

    :param request: Pyramid request object
    :return: The session user
    :rtype: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    """
    if _EDIT_USER in request.session:
        user = request.session[_EDIT_USER]
    else:
        user = request.session[_USER]
    return user


def get_logged_in_user(request, legacy_user=False, raise_on_not_logged_in=True):
    """
    Get the currently logged in user.

    :param request: Pyramid request object

    :return: The logged in user
    :rtype: eduid_userdb.User | eduid_userdb.dashboard.DashboardLegacyUser
    """
    if not raise_on_not_logged_in and _USER not in request.session:
        return None
    user = request.session[_USER]
    return user
