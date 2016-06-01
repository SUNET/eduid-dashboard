#from bleach import clean
from hashlib import sha256
from urllib import unquote, quote
from uuid import uuid4
import re
import time
import pytz
import logging
from pwgen import pwgen
from bleach import clean

from pyramid.i18n import TranslationString as _
from pyramid.httpexceptions import HTTPForbidden, HTTPBadRequest

from eduiddashboard.compat import text_type

from eduid_userdb.exceptions import UserDBValueError


logger = logging.getLogger(__name__)


# http://www.regular-expressions.info/email.html
RFC2822_email = re.compile("(?i)[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/="
                           "?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\."
                           ")+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")


def verify_auth_token(shared_key, eppn, token, nonce, timestamp, generator=sha256):
    # check timestamp to make sure it is within 300 seconds from now
    """
    Authenticate user who just signed up, that haven't confirmed their e-mail
    address yet and therefor not rececived their real password yet.

    Authentication is done using a shared secret in the configuration of the
    dashboard and signup applications. The signup application can effectively
    log a new user into the dashboard.

    :param shared_key: auth_token string from configuration
    :param eppn: the identifier of the user as string
    :param token: authentication token as string
    :param nonce: a public nonce for this authentication request as string
    :param timestamp: unixtime of signup application as hex string
    :param generator: hash function to use (default: SHA-256)
    :return: bool, True on valid authentication
    """
    logger.debug("Trying to authenticate user {!r} with auth token {!r}".format(eppn, token))
    # check timestamp to make sure it is within -300..900 seconds from now
    now = int(time.time())
    ts = int(timestamp, 16)
    if (ts < now - 300) or (ts > now + 900):
        logger.debug("Auth token timestamp {!r} out of bounds ({!s} seconds from {!s})".format(
            timestamp, ts - now, now))
        raise HTTPForbidden(_('Login token expired, please await confirmation e-mail to log in.'))
    # verify there is a long enough nonce
    if len(nonce) < 16:
        logger.debug("Auth token nonce {!r} too short".format(nonce))
        raise HTTPForbidden(_('Login token invalid'))

    expected = generator("{0}|{1}|{2}|{3}".format(
        shared_key, eppn, nonce, timestamp)).hexdigest()
    # constant time comparision of the hash, courtesy of
    # http://rdist.root.org/2009/05/28/timing-attack-in-google-keyczar-library/
    if len(expected) != len(token):
        logger.debug("Auth token bad length")
        raise HTTPForbidden(_('Login token invalid'))
    result = 0
    for x, y in zip(expected, token):
        result |= ord(x) ^ ord(y)
    logger.debug("Auth token match result: {!r}".format(result == 0))
    return result == 0


def flash(request, message_type, message):
    request.session.flash(u"{0}|{1}".format(message_type, message))


def get_icon_string(status):
    return "icon-{0}".format(status)


def filter_tabs(tabs, remove_tabs):
    return filter(lambda tab: tab['id'] not in remove_tabs, tabs)


def get_available_tabs(context, request):
    from eduiddashboard.views import (emails, personal,
                                      mobiles, nins, permissions,
                                      get_dummy_status)

    default_tabs = [
        personal.get_tab(request),
        nins.get_tab(request),
        emails.get_tab(request),
        permissions.get_tab(request),
        mobiles.get_tab(request),
        # postal_address.get_tab(request),
        {
            'label': _('Security'),
            'status': get_dummy_status,
            'id': 'security',
        },
    ]
    if context.workmode == 'personal':
        tabs = filter_tabs(default_tabs, ['permissions'])
    elif context.workmode == 'helpdesk':
        tabs = filter_tabs(default_tabs, ['passwords', 'authorization'])
    else:
        tabs = default_tabs
    for tab in tabs:
        tab['status'] = tab['status'](request, context.user)
    return tabs


def calculate_filled_profile(tabs):
    tuples = []
    for tab in tabs:
        status = tab['status']
        if status is not None:
            tuples.append(status.get('completed'))

    filled_profile = [sum(a) for a in zip(*tuples)]
    return int((float(filled_profile[0]) / float(filled_profile[1])) * 100)


def get_pending_actions(user, tabs):
    tuples = []
    for tab in tabs:
        if tab['status'] is not None:
            status = tab['status']
            if status and 'pending_actions' in status:
                tuples.append((
                    tab['id'],
                    status['pending_actions'],
                    status['pending_action_type'],
                    status['verification_needed'],
                ))

    return tuples


def get_unique_hash():
    return text_type(uuid4())


def get_short_hash(entropy=10):
    return uuid4().hex[:entropy]


def generate_password(length=12):
    return pwgen(int(length), no_capitalize=True, no_symbols=True)


def normalize_email(addr):
    return addr.lower()


def validate_email_format(email):
    return RFC2822_email.match(email)


def normalize_to_e_164(request, mobile):
    if mobile.startswith(u'0'):
        country_code = request.registry.settings.get('default_country_code')
        return country_code + mobile.lstrip(u'0')
    return mobile


def convert_to_localtime(dt):
    """
    Convert UTC datetime to localtime timezone ('Europe/Stockholm')

    @param dt: datetime utc object
    @type dt: datetime
    @return: datetime object converted to timezone Europe/Stockholm
    @rtype: datetime
    """
    tz = pytz.timezone('Europe/Stockholm')
    dt = dt.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(tz)
    return dt


def retrieve_modified_ts(user, dashboard_userdb):
    """
    When loading a user from the central userdb, the modified_ts has to be
    loaded from the dashboard private userdb (since it is not propagated to
    'attributes' by the eduid-am worker).

    This need should go away once there is a global version number on the user document.

    :param user: User object from the central userdb
    :param dashboard_userdb: Dashboard private userdb

    :type user: eduid_userdb.User
    :type dashboard_userdb: eduid_userdb.dashboard.DashboardUserDB

    :return: None
    """
    try:
        userid = user.user_id
    except UserDBValueError:
        logger.debug("User {!s} has no id, setting modified_ts to None".format(user))
        user.modified_ts = None
        return

    dashboard_user = dashboard_userdb.get_user_by_id(userid, raise_on_missing=False)
    if dashboard_user is None:
        logger.debug("User {!s} not found in {!s}, setting modified_ts to None".format(user, dashboard_userdb))
        user.modified_ts = None
        return

    if dashboard_user.modified_ts is None:
        dashboard_user.modified_ts = True  # use current time
        logger.debug("Updating user {!s} with new modified_ts: {!s}".format(
            dashboard_user, dashboard_user.modified_ts))
        dashboard_userdb.save(dashboard_user, check_sync = False)

    user.modified_ts = dashboard_user.modified_ts
    logger.debug("Updating {!s} with modified_ts from dashboard user {!s}: {!s}".format(
        user, dashboard_user, dashboard_user.modified_ts))


def sanitize_get(request, *args):
    """
    Wrapper around request.GET.get() to sanitize untrusted user input.
    """
    return _sanitize_common(request, 'GET', *args)


def sanitize_session_get(request, *args):
    """
    Wrapper around request.session.get() to sanitize untrusted input.
    """
    return _sanitize_common(request, 'session', *args)

def sanitize_cookies_get(request, *args):
    """
    Wrapper around request.cookie.get() to sanitize untrusted input.
    """
    return _sanitize_common(request, 'cookies', *args)


def sanitize_post_key(request, *args):
    """
    Wrapper around self.request.POST.get() to sanitize untrusted user input.
    """
    return _sanitize_common(request, 'POST', *args)


def sanitize_post_multidict(request, post_parameter):
    """
    Wrapper around self.request.POST['parameter'] to sanitize user input.
    """
    try:
        return _sanitize_common(request, 'POST', post_parameter)
    except KeyError:
        logger.warn('An unexpected error occurred: POST parameter {!r} '
                    'could not be found in the request.'.format(post_parameter))

        # Re-raise the exception to not change the
        # expected logic of the wrapped function.
        raise


def _sanitize_common(request, function_attribute, *args):
    """
    Wrapper around request.GET.get() to sanitize the GET request by using
    bleach as recommended by OWASP and take care of illegal UTF-8, which
    is not properly handled in webob as seen in this unfixed bug:
    https://github.com/Pylons/webob/issues/161.

    :param request: The webob request object
    :param function_attribute: Function attribute returning the desired information
    :param args: Parameter name and possibly default value

    :return: Sanitized user input
    :rtype: str | unicode
    """
    try:
        if hasattr(request, 'content_type'):
            return sanitize_input(getattr(request, function_attribute).get(*args),
                                  content_type=request.content_type)
        else:
            # The DummyRequest class used for testing has no attribute content_type
            return sanitize_input(getattr(request, function_attribute).get(*args))
    except UnicodeDecodeError:
        logger.warn('A malicious user tried to crash the application '
                    'by sending non-unicode input in a {!r} request'
                    .format(function_attribute))
        raise HTTPBadRequest("Non-unicode input, please try again.")


def sanitize_input(untrusted_text, strip_characters=False,
                   content_type=None, percent_encoded=False):
    """
    Sanitize user input by escaping or removing potentially
    harmful input using a whitelist-based approach with
    bleach as recommended by OWASP.

    :param untrusted_text User input to sanitize
    :param strip_characters Set to True to remove instead of escaping
                            potentially harmful input.

    :param content_type Set to decide on the use of percent encoding
                        according to the content type.

    :param percent_encoded Set to True if the input should be treated
                           as percent encoded if no content type is
                           already defined.

    :return: Sanitized user input

    :type untrusted_text: str | unicode
    :rtype: str | unicode
    """
    if untrusted_text is None:
        # If we are given None then there's nothing to clean
        return None

    # Decide on whether or not to use percent encoding:
    # 1. Check if the content type has been explicitly set
    # 2. If set, use percent encoding if requested by the client
    # 3. If the content type has not been explicitly set,
    # 3.1 use percent encoding according to the calling
    #    functions preference or,
    # 3.2 use the default value as set in the function definition.
    if content_type is not None:

        if content_type == "application/x-www-form-urlencoded":
            use_percent_encoding = True
        else:
            use_percent_encoding = False

    else:
        use_percent_encoding = percent_encoded

    if use_percent_encoding:
        # If the untrusted_text is percent encoded we have to:
        # 1. Decode it so we can process it.
        # 2. Encode it to UTF-8 since bleach assumes this encoding
        # 3. Clean it to remove dangerous characters.
        # 4. Percent encode it before returning it back.

        decoded_text = unquote(untrusted_text)

        if not isinstance(decoded_text, unicode):
            decoded_text_in_utf8 = decoded_text.encode("UTF-8")
        else:
            decoded_text_in_utf8 = decoded_text

        cleaned_text = _safe_clean(decoded_text_in_utf8, strip_characters)
        percent_encoded_text = quote(cleaned_text)

        if decoded_text_in_utf8 != cleaned_text:
            logger.warn('Some potential harmful characters were '
                        'removed from untrusted user input.')

        return percent_encoded_text

    # If the untrusted_text is not percent encoded we only have to:
    # 1. Encode it to UTF-8 since bleach assumes this encoding
    # 2. Clean it to remove dangerous characters.

    if not isinstance(untrusted_text, unicode):
        text_in_utf8 = untrusted_text.encode("UTF-8")
    else:
        text_in_utf8 = untrusted_text

    cleaned_text = _safe_clean(text_in_utf8, strip_characters)

    if text_in_utf8 != cleaned_text:
        logger.warn('Some potential harmful characters were '
                    'removed from untrusted user input.')

    return cleaned_text


def _safe_clean(untrusted_text, strip_characters=False):
    """
    Wrapper for the clean function of bleach to be able
    to catch when illegal UTF-8 is processed.

    :param untrusted_text: Text to sanitize
    :param strip_characters: Set to True to remove instead of escaping
    :return: Sanitized text

    :type untrusted_text: str | unicode
    :rtype: str | unicode
    """
    try:
        return clean(untrusted_text, strip=strip_characters)
    except KeyError:
        logger.warn('A malicious user tried to crash the application by '
                    'sending illegal UTF-8 in an URI or other untrusted '
                    'user input.')
        raise HTTPBadRequest("Non-unicode input, please try again.")

