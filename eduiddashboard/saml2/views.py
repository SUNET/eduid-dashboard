import logging

from saml2 import BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.metadata import entity_descriptor

from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from pyramid.security import remember

from eduiddashboard.saml2.utils import get_saml2_config, get_location


logger = logging.getLogger(__name__)


@view_config(route_name='saml2-login')
def login(request):
    login_redirect_url = request.registry.settings.get('saml2.login_redirect_url', '/')

    came_from = request.GET.get('next', login_redirect_url)

    if request.session.get('is_logged', False):
        HTTPFound(came_from)

    selected_idp = request.GET.get('idp', None)
    conf = get_saml2_config(request.registry.settings.get('saml2.settings_module'))

    # is a embedded wayf needed?
    idps = conf.getattr('idp', 'sp')
    if selected_idp is None and len(idps) > 1:
        logger.debug('A discovery process is needed')

        return render_to_response('eduiddashboard:templates/wayf.jinja2', {
            'available_idps': idps.items(),
            'came_from': came_from,
        })

    client = Saml2Client(conf)
    try:
        (session_id, result) = client.prepare_for_authenticate(
            entityid=selected_idp, relay_state=came_from,
            binding=BINDING_HTTP_REDIRECT,
        )
    except TypeError, e:
        logger.error('Unable to know which IdP to use')
        raise unicode(e)

    request.session['saml_session_id'] = session_id

    logger.debug('Redirecting the user to the IdP')
    return HTTPFound(get_location(result))


@view_config(route_name='saml2-acs', request_method='POST')
def assertion_consumer_service(request):
    raise NotImplemented()


@view_config(route_name='saml2-echo-attributes')
def echo_attributes(request):
    raise NotImplemented()


@view_config(route_name='saml2-logout')
def logout(request):
    raise NotImplemented()


@view_config(route_name='saml2-logout-service')
def logout_service(request):
    raise NotImplemented()


@view_config(route_name='saml2-metadata')
def metadata(request):
    raise NotImplemented()
