import os

from pyramid.authentication import (AuthTktAuthenticationPolicy,
                                    SessionAuthenticationPolicy)
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import ConfigurationError

from eduiddashboard.saml2.utils import get_saml2_config_from_request


def read_setting_from_env(settings, key, default=None):
    env_variable = key.upper()
    if env_variable in os.environ:
        return os.environ[env_variable]
    else:
        return settings.get(key, default)


def configure_auth(config, settings):

    extra_authn_policy = {}

    if 'groups_callback' in settings:
        extra_authn_policy['callback'] = settings['groups_callback']

    if not settings.get('testing'):
        authn_policy = SessionAuthenticationPolicy(prefix='session',
                                                   **extra_authn_policy)
    else:
        authn_policy = AuthTktAuthenticationPolicy(
            settings.get('auth_tk_secret', '1234'),
            hashalg='sha512',
            wild_domain=False,
            **extra_authn_policy)

    authz_policy = ACLAuthorizationPolicy()

    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    return config


def includeme(config):
    settings = config.registry.settings

    for item in (
        'saml2.settings_module',
        'saml2.login_redirect_url',
        'saml2.logout_redirect_url',
        'saml2.user_main_attribute',
    ):
        settings[item] = read_setting_from_env(settings, item, None)
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    config.add_request_method(get_saml2_config_from_request, 'saml2_config',
                              reify=True)

    if settings.get('testing', False):
        from eduiddashboard.saml2.testing import MockedUserDB

        # Create mock userdb instance and store it in our config,
        # and make a getter lambda for pyramid to retreive it
        userdb = MockedUserDB()
        config.registry.settings['userdb'] = userdb
        config.add_request_method(lambda x: x.registry.settings['userdb'], 'userdb', reify=True)

    config = configure_auth(config, settings)
    # saml2 views
    config.add_route('saml2-login', '/saml2/login/')
    config.add_route('saml2-acs', '/saml2/acs/')
    config.add_route('saml2-echo-attributes', '/saml2/echo-attributes/')
    config.add_route('saml2-logout', '/saml2/logout/')
    config.add_route('saml2-logout-service', '/saml2/ls/')
    config.add_route('saml2-metadata', '/saml2/metadata/')

    config.add_route('saml2-wayf-demo', '/saml2/wayf-demo/')
    config.add_route('saml2-forbidden-view', '/saml2/forbidden/')
