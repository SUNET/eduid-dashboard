import logging
import urlparse
from urllib import urlencode

from pyramid.httpexceptions import HTTPFound

from eduiddashboard.session import get_session_user

log = logging.getLogger(__name__)


def reauthn_ts_tween_factory(handler, registry):

    def clean_reauthn_ts_from_session(request):
        response = handler(request)
        path = request.get('SCRIPT_NAME', '') + request.get('PATH_INFO', '')
        acs_path = request.route_path('saml2-acs')
        try:
            chp_path = request.route_path('password-change')
        except KeyError:
            # too early to continue
            return response
        referer = request.referer
        acs_url = request.route_url('saml2-acs')
        chp_url = request.route_url('password-change')

        if (path != acs_path and
            path != chp_path and
            acs_url != referer and
            chp_url != referer and
            request.session.get('re-authn-ts', False)):
            user = get_session_user(request)
            log.debug('Removing stale Authn ts for user {!r} '.format(user))
            del request.session['re-authn-ts']

        return response

    return clean_reauthn_ts_from_session


def authn_tween_factory(handler, registry):

    def check_authn(request):
        settings = registry.settings
        cookie_name = settings.get('SESSION_COOKIE_NAME')
        if request.cookies and cookie_name in request.cookies:
            return handler(request)
        ts_url = settings.get('token_service_url')
        next_url = request.url

        params = {'next': next_url}

        url_parts = list(urlparse.urlparse(ts_url))
        query = urlparse.parse_qs(url_parts[4])
        query.update(params)

        url_parts[4] = urlencode(query)
        location = urlparse.urlunparse(url_parts)

        return HTTPFound(location=location)
    return check_authn
