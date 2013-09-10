import os

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.exceptions import ConfigurationError

from eduiddashboard.saml2.utils import get_saml2_config_from_request


def read_setting_from_env(settings, key, default=None):
    env_variable = key.upper()
    if env_variable in os.environ:
        return os.environ[env_variable]
    else:
        return settings.get(key, default)


def configure_authtk(config, settings):

    extra_authn_policy = {}

    if 'groups_callback' in settings:
        extra_authn_policy['callback'] = settings['groups_callback']

    authn_policy = AuthTktAuthenticationPolicy(
        settings['auth_tk_secret'], hashalg='sha512',
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
        'saml2.user_main_attribute',
        'auth_tk_secret'
    ):
        settings[item] = read_setting_from_env(settings, item, None)
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    attribute_mapping_raw = read_setting_from_env(settings,
                                                  'saml2.attribute_mapping',
                                                  "")

    attribute_mapping = {}
    for raw_line in attribute_mapping_raw.split('\n'):
        if '=' in raw_line:
            (from_saml2, to_local) = raw_line.split('=')
            from_saml2 = from_saml2.strip()
            to_local = to_local.strip()
            if from_saml2 not in attribute_mapping:
                attribute_mapping[from_saml2] = [to_local]
            else:
                attribute_mapping[from_saml2].append(to_local)

    if attribute_mapping == {}:
        raise ConfigurationError(
            'The saml2.attribute_mapping configuration option is required. '
            'Remember you must use one line per attribute with the follow '
            'format: saml_attribute=local_attribute')

    settings['saml2.attribute_mapping'] = attribute_mapping

    config.add_request_method(get_saml2_config_from_request, 'saml2_config',
                              reify=True)

    if settings.get('testing', False):
        from eduiddashboard.saml2.testing import MockedUserDB
        userdb = MockedUserDB()

        def get_userdb(request):
            return config.registry.settings['userdb']

        config.registry.settings['userdb'] = userdb
        config.add_request_method(get_userdb, 'userdb', reify=True)

    # saml2 views
    config.add_route('saml2-login', '/saml2/login/')
    config.add_route('saml2-acs', '/saml2/acs/')
    config.add_route('saml2-echo-attributes', '/saml2/echo-attributes/')
    config.add_route('saml2-logout', '/saml2/logout/')
    config.add_route('saml2-logout-service', '/saml2/slo/')
    config.add_route('saml2-metadata', '/saml2/metadata/')

    config.add_route('saml2-wayf-demo', '/saml2/wayf-demo/')
    config.add_route('saml2-forbidden-view', '/saml2/forbidden/')
