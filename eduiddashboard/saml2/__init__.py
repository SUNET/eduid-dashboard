import os

from pyramid.exceptions import ConfigurationError

from eduiddashboard.saml2.utils import get_saml2_config


def read_setting_from_env(settings, key, default=None):
    env_variable = key.upper()
    if env_variable in os.environ:
        return os.environ[env_variable]
    else:
        return settings.get(key, default)


def includeme(config):
    settings = config.registry.settings

    for item in (
        'saml2.settings_module',
        'saml2.login_redirect_url',
    ):
        settings[item] = read_setting_from_env(settings, item, None)
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    saml2_config = get_saml2_config(settings.get('saml2.settings_module'))
    config.set_request_property(saml2_config, 'saml2_config', reify=True)

    # saml2 views
    config.add_route('saml2-login', '/saml2/login/')
    config.add_route('saml2-acs', '/saml2/acs/')
    config.add_route('saml2-echo-attributes', '/saml2/echo-attributes/')
    config.add_route('saml2-logout', '/saml2/logout/')
    config.add_route('saml2-logout-service', '/saml2/slo/')
    config.add_route('saml2-metadata', '/saml2/metadata/')
