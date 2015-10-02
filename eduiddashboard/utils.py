from bleach import clean
from hashlib import sha256
from urllib import unquote, quote
from uuid import uuid4
import re
import time
import pytz
from pwgen import pwgen

from pyramid.i18n import TranslationString as _

from eduiddashboard.compat import text_type

from eduiddashboard import AVAILABLE_LOA_LEVEL

from pyramid.httpexceptions import HTTPForbidden, HTTPBadRequest

import logging

logger = logging.getLogger(__name__)

MAX_LOA_ROL = {
    'user': AVAILABLE_LOA_LEVEL[0],
    'helpdesk': AVAILABLE_LOA_LEVEL[1],
    'admin': AVAILABLE_LOA_LEVEL[2],
}

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
        tab['status'] = tab['status'](context.request, context.user)
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


def get_max_available_loa(groups):
    if not groups:
        return MAX_LOA_ROL['user']
    loas = [v for (k, v) in MAX_LOA_ROL.iteritems() if k in groups]
    if len(loas) > 0:
        return max(loas)
    else:
        return MAX_LOA_ROL['user']


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


def sanitize_get(request, *args):
    """
    Sanitize the GET request by using bleach as recommended by OWASP and
    take care of illegal UTF-8, which is not properly handled in webob as
    seen in this unfixed bug: https://github.com/Pylons/webob/issues/161.

    :param request: The webob request object
    :param args: The arguments to send to webob
    :return: A sanitized GET request
    """
    try:
        return sanitize_input(request.GET.get(*args))
    except UnicodeDecodeError:
        logger.warn('A malicious user tried to crash the application '
                    'by sending non-unicode input in a GET request')
        raise HTTPBadRequest("Non-unicode input, please try again.")


def sanitize_session_get(request, *args):
    """
    Sanitize the GET request by using bleach as recommended by OWASP and
    take care of illegal UTF-8, which is not properly handled in webob as
    seen in this unfixed bug: https://github.com/Pylons/webob/issues/161.

    :param request: The webob request object
    :param args: The arguments to send to webob
    :return: A sanitized GET request
    """
    try:
        return sanitize_input(request.session.get(*args))
    except UnicodeDecodeError:
        logger.warn('A malicious user tried to crash the application '
                    'by sending non-unicode input in a GET request')
        raise HTTPBadRequest("Non-unicode input, please try again.")


def sanitize_post_get(request, *args):
    """
    Sanitize the POST request by using bleach as recommended by OWASP and
    take care of illegal UTF-8, which is not properly handled in webob as
    seen in this unfixed bug: https://github.com/Pylons/webob/issues/161.

    :param request: The webob request object
    :param args: The arguments to send to webob
    :return: A sanitized POST request
    """
    try:
        return sanitize_input(request.POST.get(*args))
    except UnicodeDecodeError:
        logger.warn('A malicious user tried to crash the application '
                    'by sending non-unicode input in a POST request')
        raise HTTPBadRequest("Non-unicode input, please try again.")


def sanitize_input(untrusted_text, strip_characters=False):
    """
    Sanitize user input by escaping or removing potentially
    harmful input using a whitelist-based approach with
    bleach as recommended by OWASP.

    :param untrusted_text User input to sanitize
    :param strip_characters Set to True to remove instead of escaping harmful input
    :return: Sanitized user input

    :type untrusted_text: string()
    :rtype: string()
    """
    try:

        if untrusted_text is None:
            # If we are given None then there's nothing to clean
            return None

        elif is_percent_encoded(untrusted_text):
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

            cleaned_text = clean(decoded_text_in_utf8, strip=strip_characters)
            percent_encoded_text = quote(cleaned_text)

            if decoded_text_in_utf8 != cleaned_text:
                logger.warn('Some potential harmful characters were '
                            'removed from untrusted user input.')

            return percent_encoded_text

        else:
            # If the untrusted_text is not percent encoded we only have to:
            # 1. Encode it to UTF-8 since bleach assumes this encoding
            # 2. Clean it to remove dangerous characters.

            if not isinstance(untrusted_text, unicode):
                text_in_utf8 = untrusted_text.encode("UTF-8")
            else:
                text_in_utf8 = untrusted_text

            cleaned_text = clean(text_in_utf8, strip=strip_characters)

            if text_in_utf8 != cleaned_text:
                logger.warn('Some potential harmful characters were '
                            'removed from untrusted user input.')

            return cleaned_text

    except KeyError:
        logger.warn('A malicious user tried to crash the application by '
                    'sending illegal UTF-8 in an URI or other untrusted '
                    'user input.')
        raise HTTPBadRequest("Non-unicode input, please try again.")


def is_percent_encoded(text):
    if text != unquote(text):
        return True
    else:
        return False
