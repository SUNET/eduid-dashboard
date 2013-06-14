import logging

from saml2 import BINDING_HTTP_REDIRECT, BINDING_HTTP_POST
from saml2.client import Saml2Client
from saml2.metadata import entity_descriptor

from pyramid.httpexceptions import (HTTPFound, HTTPBadRequest,
                                    HTTPUnauthorized, HTTPForbidden)
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.security import authenticated_userid
from pyramid.view import view_config, forbidden_view_config

from eduiddashboard.saml2.utils import get_saml2_config, get_location
from eduiddashboard.saml2.auth import authenticate, login
from eduiddashboard.saml2.cache import IdentityCache, OutstandingQueriesCache


logger = logging.getLogger(__name__)


def _set_subject_id(session, subject_id):
    session['_saml2_subject_id'] = subject_id


def _get_subject_id(session):
    return session['_saml2_subject_id']


@forbidden_view_config()
def forbidden_view(request):
    # do not allow a user to login if they are already logged in
    if authenticated_userid(request):
        return HTTPForbidden()

    loc = request.route_url('saml2-login',
                            _query=(('next', request.path),))
    return HTTPFound(location=loc)


@view_config(route_name='saml2-login')
def login_view(request):
    login_redirect_url = request.registry.settings.get(
        'saml2.login_redirect_url', '/')

    came_from = request.GET.get('next', login_redirect_url)

    if authenticated_userid(request):
        HTTPFound(came_from)

    selected_idp = request.GET.get('idp', None)

    # is a embedded wayf needed?
    idps = request.saml2_config.getattr('idp', 'sp')
    if selected_idp is None and len(idps) > 1:
        logger.debug('A discovery process is needed')

        return render_to_response('eduiddashboard:templates/wayf.jinja2', {
            'available_idps': idps.items(),
            'came_from': came_from,
        })

    client = Saml2Client(request.saml2_config)
    try:
        (session_id, result) = client.prepare_for_authenticate(
            entityid=selected_idp, relay_state=came_from,
            binding=BINDING_HTTP_REDIRECT,
        )
    except TypeError, e:
        logger.error('Unable to know which IdP to use')
        raise unicode(e)

    oq_cache = OutstandingQueriesCache(request.session)
    oq_cache.set(session_id, came_from)

    logger.debug('Redirecting the user to the IdP')
    return HTTPFound(location=get_location(result))


@view_config(route_name='saml2-acs', request_method='POST')
def assertion_consumer_service(request):
    attribute_mapping = request.registry.settings['saml2.attribute_mapping']

    client = Saml2Client(request.saml2_config)

    if 'SAMLResponse' not in request.POST:
        return HTTPBadRequest(
            'Couldn\'t find "SAMLResponse" in POST data.')
    xmlstr = request.POST['SAMLResponse']
    client = Saml2Client(request.saml2_config,
                         identity_cache=IdentityCache(request.session))

    oq_cache = OutstandingQueriesCache(request.session)
    outstanding_queries = oq_cache.outstanding_queries()

    # process the authentication response
    response = client.parse_authn_request_response(xmlstr, BINDING_HTTP_POST,
                                                   outstanding_queries)
    if response is None:
        logger.error('SAML response is None')
        return HTTPBadRequest(
            "SAML response has errors. Please check the logs")

    session_id = response.session_id()
    oq_cache.delete(session_id)

    # authenticate the remote user
    session_info = response.session_info()

    logger.debug('Trying to authenticate the user')

    user = authenticate(request, session_info, attribute_mapping)
    if user is None:
        logger.error('The user is None')
        return HTTPUnauthorized("Access not authorized")

    headers = login(request, session_info, user)

    _set_subject_id(request.session, session_info['name_id'])

    # redirect the user to the view where he came from
    relay_state = request.POST.get('RelayState', '/')
    logger.debug('Redirecting to the RelayState: ' + relay_state)
    return HTTPFound(location=relay_state, headers=headers)


@view_config(route_name='saml2-echo-attributes')
def echo_attributes(request):
    raise NotImplementedError


@view_config(route_name='saml2-logout')
def logout(request):
    raise NotImplementedError


@view_config(route_name='saml2-logout-service')
def logout_service(request):
    raise NotImplementedError


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
