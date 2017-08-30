import logging
import urlparse
import time
from urllib import urlencode

from pyramid.security import remember
from pyramid.httpexceptions import HTTPFound

from eduiddashboard.utils import sanitize_post_key
from eduid_common.api.utils import urlappend


log = logging.getLogger(__name__)


def authn_tween_factory(handler, registry):

    def check_authn(request):
        settings = registry.settings
        cookie_name = settings.get('session.key')
        next_url = None
        if ((cookie_name in request.cookies and 'eduPersonPrincipalName' in request.session) or
                len([param for param in ['eppn', 'token', 'ts', 'nonce'] if param in request.params]) == 4):
            try:
                remember(request, request.session['eduPersonPrincipalName'])
                return handler(request)
            except KeyError:
                # we have just signed up, there is no eppn in the session,
                # we must have it as a request.param
                log.info("Trying to authenticate user ({}) with signup auth token".format(request.params['eppn']))
                # XXX Duplicated token expire time check from verify_auth_token
                # check timestamp to make sure it is within -300..900 seconds from now
                now = int(time.time())
                ts = int(request.params['ts'], 16)
                if (ts > now - 300) and (ts < now + 900):
                    # Token seems recent, continue to token view
                    eppn = request.params['eppn']
                    remember(request, eppn)
                    request.session['eduPersonPrincipalName'] = eppn
                    return handler(request)
                # Token has expired, do not refer user to token_login view after login
                next_url = request.route_url('profile-editor')
                log.debug("Auth token timestamp {!r} out of bounds ({!s} seconds from {!s})".format(
                    request.params['ts'], ts - now, now))

        try:
            reset_password_url = request.route_url('reset-password')
        except KeyError:
            pass
        else:
            if reset_password_url in request.url:
                return handler(request)

        login_url = urlappend(settings['token_service_url'], 'login')
        if next_url is None:
            next_url = sanitize_post_key(request, 'next_url', '/')

        params = {'next': next_url}

        url_parts = list(urlparse.urlparse(login_url))
        query = urlparse.parse_qs(url_parts[4])
        query.update(params)

        url_parts[4] = urlencode(query)
        location = urlparse.urlunparse(url_parts)

        request.session.persist()
        request.session.set_cookie()
        return HTTPFound(location=location)

    return check_authn
