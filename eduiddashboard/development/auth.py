# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from pyramid.security import remember
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from eduiddashboard import log


def setup_auth(config):
    """
    Used to set up minimal authentication/authorization parameters.
    """
    config.add_route('saml2-login', '/saml2/login/')
    config.add_route('saml2-logout', '/saml2/logout/')

    settings = config.registry.settings
    extra_authn_policy = {}

    if 'groups_callback' in settings:
        extra_authn_policy['callback'] = settings['groups_callback']

    authn_policy = SessionAuthenticationPolicy(prefix='session', **extra_authn_policy)
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    return config


def login(request, username):
    """
    Used to set up minimal session parameters for a user.
    """
    user = request.userdb.get_user('%s@example.com' % username)

    if username == 'admin':
        al_level = 'http://www.swamid.se/policy/assurance/al3'
        urn = ['urn:mace:eduid.se:role:admin']
    elif username == 'helpdesk':
        al_level = 'http://www.swamid.se/policy/assurance/al2'
        urn = ['urn:mace:eduid.se:role:ra']
    else:
        al_level = 'http://www.swamid.se/policy/assurance/al1'
        urn = ''

    main_attribute = request.registry.settings.get('saml2.user_main_attribute')
    request.session[main_attribute] = user[main_attribute]
    request.session['user'] = user
    request.session['user']['eduPersonEntitlement'] = urn
    request.session['eduPersonAssurance'] = al_level
    headers = remember(request, user[main_attribute])
    return request, headers