import pprint

from saml2 import BINDING_HTTP_REDIRECT, BINDING_HTTP_POST
from saml2.client import Saml2Client
from saml2.metadata import entity_descriptor
from saml2.response import LogoutResponse
from saml2.saml import AuthnContextClassRef
from saml2.samlp import RequestedAuthnContext


from pyramid.httpexceptions import (HTTPFound, HTTPBadRequest, HTTPNotFound,
                                    HTTPUnauthorized, HTTPInternalServerError,
                                    HTTPOk)
from pyramid.response import Response
from pyramid.renderers import render_to_response, render
from pyramid.security import authenticated_userid
from pyramid.view import view_config, forbidden_view_config

from eduiddashboard.saml2.utils import get_saml2_config, get_location
from eduiddashboard.utils import sanitize_input, sanitize_get, sanitize_session_get
from eduiddashboard.saml2.auth import authenticate, login, logout
from eduiddashboard.saml2.cache import (IdentityCache, OutstandingQueriesCache,
                                        StateCache, )
from eduiddashboard.saml2.acs_actions import (acs_action,
                                              schedule_action,
                                              get_action)

from eduiddashboard import log


class HTTPXRelocate(HTTPOk):

    empty_body = True

    def __init__(self, new_location, **kwargs):
        super(HTTPXRelocate, self).__init__('', headers=[
            ('X-Relocate', new_location),
            ('Content-Type', 'text/html; charset=UTF-8'),
        ])


def _set_name_id(session, name_id):
    """
    Store SAML2 name id info.

    :param session: The current session object
    :param name_id: saml2.saml.NameID object
    :return: None

    :type name_id: saml2.saml.NameID
    """
    session['_saml2_session_name_id'] = name_id


def _get_name_id(session):
    """
    Get the SAML2 NameID of the currently logged in user.

    :param session: The current session object
    :return: NameID
    :rtype: saml2.saml.NameID | None
    """
    try:
        return session['_saml2_session_name_id']
    except KeyError:
        return None


@forbidden_view_config()
@view_config(route_name='saml2-forbidden-view')
def forbidden_view(context, request):
    """
    View to trap all Forbidden errors and redirect any not logged in users to the login page.

    For logged in users, a template is rendered - this template probably won't be seen
    by the user though since there is Javascript handling 401 errors from form posts
    showing a small pop-up error message instead.
    :param context: Some object like HTTPForbidden()
    :param request: Request() object
    :return:
    """
    user = authenticated_userid(request)
    if user:
        # Return a plain forbidden page
        try:
            reason = context.explanation
        except AttributeError:
            reason = 'unknown'
        log.debug("User {!r} tripped Forbidden view, request {!r}, reason {!r}".format(
            user, request, reason))
        response = Response(render('templates/forbidden.jinja2', {}))
        response.status_int = 401
        return response

    loginurl = request.route_url('saml2-login',
                                _query=(('next', request.path),))
    if not request.is_xhr:
        return HTTPFound(location=loginurl)
    else:
        return HTTPXRelocate(loginurl)


@acs_action('login-action')
def login_action(request, session_info, user):

    headers = login(request, session_info, user)
    _set_name_id(request.session, session_info['name_id'])

    # redirect the user to the view where he came from
    relay_state = request.POST.get('RelayState', '/')
    log.debug('Redirecting to the RelayState: ' + relay_state)
    return HTTPFound(location=relay_state, headers=headers)


@view_config(route_name='saml2-login')
def login_view(request):
    login_redirect_url = request.registry.settings.get(
        'saml2.login_redirect_url', '/')

    came_from = sanitize_get(request, 'next', login_redirect_url)

    if authenticated_userid(request):
        return HTTPFound(location=came_from)

    selected_idp = sanitize_get(request, 'idp', None)
    if selected_idp is not None:
        request.session['selected_idp'] = selected_idp

    idps = request.saml2_config.getattr('idp')
    if selected_idp is None and len(idps) > 1:
        log.debug('A discovery process is needed')

        return render_to_response('templates/wayf.jinja2', {
            'available_idps': idps.items(),
            'came_from': came_from,
            'login_url': request.route_url('saml2-login'),
        })

    result = get_authn_request(request, came_from, selected_idp)

    schedule_action(request.session, 'login-action')

    log.debug('Redirecting the user to the IdP')
    if not request.is_xhr:
        return HTTPFound(location=get_location(result))
    else:
        loginurl = request.route_url('saml2-login',
                                     _query=(('next', request.path),))
        return HTTPXRelocate(loginurl)


@view_config(route_name='saml2-acs', request_method='POST')
def assertion_consumer_service(request):
    ''' '''
    action = get_action(request.session)

    if 'SAMLResponse' not in request.POST:
        raise HTTPBadRequest("Couldn't find 'SAMLResponse' in POST data.")
    xmlstr = request.POST['SAMLResponse']
    client = Saml2Client(request.saml2_config,
                         identity_cache=IdentityCache(request.session))

    oq_cache = OutstandingQueriesCache(request.session)
    outstanding_queries = oq_cache.outstanding_queries()

    try:
        # process the authentication response
        response = client.parse_authn_request_response(xmlstr, BINDING_HTTP_POST,
                                                       outstanding_queries)
    except AssertionError:
        log.error('SAML response is not verified')
        raise HTTPBadRequest(
            """SAML response is not verified. May be caused by the response
            was not issued at a reasonable time or the SAML status is not ok.
            Check the IDP datetime setup""")

    if response is None:
        log.error('SAML response is None')
        raise HTTPBadRequest(
            "SAML response has errors. Please check the logs")

    session_id = response.session_id()
    oq_cache.delete(session_id)

    # authenticate the remote user
    session_info = response.session_info()

    log.debug('Trying to locate the user authenticated by the IdP')
    log.debug('Session info:\n{!s}\n\n'.format(pprint.pformat(session_info)))

    user = authenticate(request, session_info)
    if user is None:
        log.error('Could not find the user identified by the IdP')
        raise HTTPUnauthorized("Access not authorized")

    return action(request, session_info, user)


@view_config(route_name='saml2-echo-attributes')
def echo_attributes(request):
    raise NotImplementedError

@view_config(route_name='saml2-logout')
def logout_view(request):
    """SAML Logout Request initiator

    This view initiates the SAML2 Logout request
    using the pysaml2 library to create the LogoutRequest.
    """
    log.debug('Logout process started')
    state = StateCache(request.session)

    client = Saml2Client(request.saml2_config, state_cache=state,
                         identity_cache=IdentityCache(request.session))
    subject_id = _get_name_id(request.session)
    if subject_id is None:
        log.warning(
            'The session does not contains the subject id for user ')
        location = request.registry.settings.get('saml2.logout_redirect_url')

    else:
        logouts = client.global_logout(subject_id)
        loresponse = logouts.values()[0]
        # loresponse is a dict for REDIRECT binding, and LogoutResponse for SOAP binding
        if isinstance(loresponse, LogoutResponse):
            if loresponse.status_ok():
                log.debug('Performing local logout of {!r}'.format(authenticated_userid(request)))
                headers = logout(request)
                location = request.registry.settings.get('saml2.logout_redirect_url')
                return HTTPFound(location=location, headers=headers)
            else:
                return HTTPInternalServerError('Logout failed')
        headers_tuple = loresponse[1]['headers']
        location = headers_tuple[0][1]

    state.sync()
    log.debug('Redirecting to {!r} to continue the logout process'.format(location))
    return HTTPFound(location=location)


@view_config(route_name='saml2-logout-service',
             renderer='templates/saml2-logout.jinja2')
def logout_service(request):
    """SAML Logout Response endpoint

    The IdP will send the logout response to this view,
    which will process it with pysaml2 help and log the user
    out.
    Note that the IdP can request a logout even when
    we didn't initiate the process as a single logout
    request started by another SP.
    """
    log.debug('Logout service started')

    state = StateCache(request.session)
    client = Saml2Client(request.saml2_config, state_cache=state,
                         identity_cache=IdentityCache(request.session))
    settings = request.registry.settings

    logout_redirect_url = settings.get('saml2.logout_redirect_url')
    next_page = sanitize_session_get(request, 'next_page', logout_redirect_url)
    next_page = sanitize_get(request, 'next_page', next_page)

    if 'SAMLResponse' in request.GET:  # we started the logout
        log.debug('Receiving a logout response from the IdP')

        # SAMLResponse is allowed to contain a lot of the
        # potentially harmful characters that we normally
        # would want to remove from user input.
        # However, if the SAMLResponse is ever to be rendered
        # and displayed, then it should of course be cleaned.
        response = client.parse_logout_request_response(
            request.GET['SAMLResponse'],
            BINDING_HTTP_REDIRECT
        )
        state.sync()
        if response and response.status_ok():
            headers = logout(request)
            return HTTPFound(next_page, headers=headers)
        else:
            log.error('Unknown error during the logout')
            return HTTPBadRequest('Error during logout')

    elif 'SAMLRequest' in request.GET:  # logout started by the IdP
        log.debug('Receiving a logout request from the IdP')
        subject_id = _get_name_id(request.session)
        if subject_id is None:
            log.warning(
                'The session does not contain the subject id for user {0} '
                'Performing local logout'.format(
                    authenticated_userid(request)
                )
            )
            headers = logout(request)
            return HTTPFound(location=next_page, headers=headers)
        else:

            # SAMLRequest and RelayState are allowed to contain a lot
            # of the potentially harmful characters that we normally
            # would want to remove from user input.
            # However, if they are ever to be rendered and
            # displayed, then they should of course be cleaned.
            http_info = client.handle_logout_request(
                request.GET['SAMLRequest'],
                subject_id,
                BINDING_HTTP_REDIRECT,
                relay_state=request.GET['RelayState']
            )
            state.sync()
            location = get_location(http_info)
            headers = logout(request)
            return HTTPFound(location=location, headers=headers)
    else:
        log.error('No SAMLResponse or SAMLRequest parameter found')
        raise HTTPNotFound('No SAMLResponse or SAMLRequest parameter found')


@view_config(route_name='saml2-metadata')
def metadata(request):
    """Returns an XML with the SAML 2.0 metadata for this
    SP as configured in the settings.py file.
    """
    conf = get_saml2_config(
        request.registry.settings.get('saml2.settings_module'))
    metadata = entity_descriptor(conf)
    return Response(body=str(metadata), content_type="text/xml; charset=utf8")


@view_config(route_name='saml2-wayf-demo',
             renderer='templates/wayf.jinja2')
def wayf_demo(request):
    return {
        'available_idps': (
            ('http://idp1.example.com', 'IDP from Organization 1'),
            ('http://idp2.example.com', 'IDP from Organization 2'),
        ),
        'came_from': '/',
        'login_url': request.route_url('saml2-login'),
    }


def get_authn_request(request, came_from, selected_idp,
                      required_loa=None, force_authn=False):
    # Request the right AuthnContext for workmode
    # (AL1 for 'personal', AL2 for 'helpdesk' and AL3 for 'admin' by default)
    if required_loa is None:
        required_loa = request.registry.settings.get('required_loa', {})
        workmode = request.registry.settings.get('workmode')
        required_loa = required_loa.get(workmode, '')
    log.debug('Requesting AuthnContext {!r}'.format(required_loa))
    kwargs = {
        "requested_authn_context": RequestedAuthnContext(
            authn_context_class_ref=AuthnContextClassRef(
                text=required_loa
            )
        ),
        "force_authn": str(force_authn).lower(),
    }

    client = Saml2Client(request.saml2_config)
    try:
        (session_id, info) = client.prepare_for_authenticate(
            entityid=selected_idp, relay_state=came_from,
            binding=BINDING_HTTP_REDIRECT,
            **kwargs
        )
    except TypeError:
        log.error('Unable to know which IdP to use')
        raise

    oq_cache = OutstandingQueriesCache(request.session)
    oq_cache.set(session_id, came_from)
    return info
