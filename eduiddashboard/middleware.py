
from pyramid.response import Response
from pyramid.i18n import get_localizer
from pyramid.httpexceptions import HTTPFound

from eduiddashboard.i18n import TranslationString as _

import logging
log = logging.getLogger(__name__)


def reauthn_ts_tween_factory(handler, registry):

    def clean_reauthn_ts_from_session(request):
        response = handler(request)
        path = request.get('PATH_INFO', '')
        acs_path = request.route_path('saml2-acs')
        try:
            chp_path = request.route_path('password-change')
        except KeyError:
            # too early to continue
            return response
        referer = request.get('HTTP_REFERER', '')
        acs_url = request.route_url('saml2-acs')
        chp_url = request.route_url('password-change')

        if (path != acs_path and
            path != chp_path and
            acs_url != referer and
            chp_url != referer and
            request.session.get('re-authn-ts', False)):
            del request.session['re-authn-ts']

        return response

    return clean_reauthn_ts_from_session


def sync_user_tween_factory(handler, registry):

    def sync_user(request):
        '''
        '''
        if request.method == 'POST':
            user = request.session.get('edit-user', None)
            if user is None:
                user = request.session.get('user', None)
            if user is not None:
                in_sync = request.userdb.in_sync(user)
                if not in_sync:
                    msg = _('The user was out of sync. Please try again.')
                    tr_msg = get_localizer(request).translate(msg)
                    if request.get('HTTP_X_REQUESTED_WITH', False):
                        msg = json.dumps({
                                'result': 'out_of_sync',
                                'message': tr_msg,
                            })
                        return Response(
                            body=json.dumps(msg),
                            status='200 Ok',
                            content_type='application/json; charset=UTF-8')
                    else:
                        request.session.flash(tr_msg)
                        return HTTPFound(location=request.route_url('profile-editor'))

        return handler(request)

    return sync_user

