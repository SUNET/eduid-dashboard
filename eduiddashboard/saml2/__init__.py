import os

from pyramid.authentication import (AuthTktAuthenticationPolicy,
                                    SessionAuthenticationPolicy)
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import ConfigurationError

from eduiddashboard.saml2.utils import (get_saml2_config_from_request,
                                        get_saml2_config)


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

    settings['SAML2_SETTINGS_MODULE'] = read_setting_from_env(settings, 'saml2.settings_module', None)
    settings['SAML2_LOGIN_REDIRECT_URL'] = read_setting_from_env(settings, 'saml2.login_redirect_url', None)
    settings['SAML2_LOGOUT_REDIRECT_URL'] = read_setting_from_env(settings, 'saml2.logout_redirect_url', None)
    for item in (
        'SAML2_SETTINGS_MODULE',
        'SAML2_LOGIN_REDIRECT_URL',
        'SAML2_LOGOUT_REDIRECT_URL',
    ):
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    settings['SAML2_STRIP_SAML_USER_SUFFIX'] = read_setting_from_env(settings, 'saml2.strip_saml_user_suffix', '')

    config.add_request_method(get_saml2_config_from_request, 'saml2_config',
                              reify=True)
    settings['SAML2_CONFIG'] = get_saml2_config(settings.get('SAML2_SETTINGS_MODULE'))

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
