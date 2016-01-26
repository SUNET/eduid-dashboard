import logging

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
            user = get_session_user(request, legacy_user = True)
            log.debug('Removing stale Authn ts for user {} '.format(user.get_id()))
            del request.session['re-authn-ts']

        return response

    return clean_reauthn_ts_from_session
