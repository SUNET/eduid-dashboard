import logging
import urlparse
from urllib import urlencode

from pyramid.security import remember
from pyramid.httpexceptions import HTTPFound

from eduid_common.api.utils import urlappend

log = logging.getLogger(__name__)


def authn_tween_factory(handler, registry):

    def check_authn(request):
        settings = registry.settings
        cookie_name = settings.get('session.key')
        if ((cookie_name in request.cookies and
                 'eduPersonPrincipalName' in request.session) or
                ('eppn' in request.params and
                 'token' in request.params and
                 'nonce' in request.params)):
            try:
                remember(request, request.session['eduPersonPrincipalName'])
            except KeyError:
                # we have just signed up, there is no eppn in the session,
                # we must have it as a request.param
                eppn = request.params['eppn']
                remember(request, eppn)
                request.session['eduPersonPrincipalName'] = eppn
            return handler(request)

        try:
            reset_password_url = request.route_url('reset-password')
        except KeyError:
            pass
        else:
            if reset_password_url in request.url:
                return handler(request)

        login_url = urlappend(settings['token_service_url'], 'login')
        next_url = request.url

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
