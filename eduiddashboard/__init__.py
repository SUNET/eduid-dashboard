import os
import re

import logging

from pkg_resources import resource_filename
from deform import Form

from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNotFound
from pyramid.settings import asbool
from pyramid.i18n import get_locale_name

from eduid_am.celery import celery
from eduid_am.db import MongoDB
from eduid_am.userdb import UserDB
from eduiddashboard.i18n import locale_negotiator
from eduiddashboard.permissions import (RootFactory, PersonFactory,
                                        SecurityFactory, ResetPasswordFactory,
                                        PostalAddressFactory, MobilesFactory,
                                        PermissionsFactory, StatusFactory,
                                        VerificationsFactory, HomeFactory,
                                        NinsFactory, ForbiddenFactory,
                                        HelpFactory, AdminFactory, is_logged)

from eduiddashboard.msgrelay import MsgRelay, get_msgrelay


AVAILABLE_WORK_MODES = ('personal', 'helpdesk', 'admin')


REQUIRED_GROUP_PER_WORKMODE = {
    'personal': '',
    'helpdesk': 'urn:mace:eduid.se:role:ra',
    'admin': 'urn:mace:eduid.se:role:admin',
}

REQUIRED_LOA_PER_WORKMODE = {
    'personal': 'http://www.swamid.se/policy/assurance/al1',
    'helpdesk': 'http://www.swamid.se/policy/assurance/al2',
    'admin': 'http://www.swamid.se/policy/assurance/al3',
}

AVAILABLE_LOA_LEVEL = [
    'http://www.swamid.se/policy/assurance/al1',
    'http://www.swamid.se/policy/assurance/al2',
    'http://www.swamid.se/policy/assurance/al3',
]


AVAILABLE_PERMISSIONS = (
    'urn:mace:eduid.se:role:ra',
    'urn:mace:eduid.se:role:admin',
)

REQUIRED_PROOFING_LINKS = (
    'nin',
)


log = logging.getLogger('eduiddashboard')


def groups_callback(userid, request):
    if getattr(request, 'context', None) is not None:
        return request.context.get_groups(userid, request)
    else:
        return []


def read_setting_from_env(settings, key, default=None):
    env_variable = key.upper()
    if env_variable in os.environ:
        return os.environ[env_variable]
    else:
        return settings.get(key, default)


def read_mapping(settings, prop, available_keys=None, default=None, required=True):
    raw = read_setting_from_env(settings, prop, '')

    if raw.strip() == '':
        return default

    rows = raw.strip('\n ').split('\n')

    mapping = {}

    for row in rows:
        splitted_row = row.split('=')
        key = row.split('=')[0].strip()
        if len(splitted_row) > 1:
            value = row.split('=')[1].strip()
        else:
            value = ''
        if available_keys is None or key in available_keys:
            mapping[key] = value

    if available_keys is not None:
        if (len(mapping.keys()) != len(available_keys) and
                not 'testing' in settings):
            return None

    return mapping


def read_list(settings, prop, default=[]):
    raw = read_setting_from_env(settings, prop, None)
    if raw is None or raw.strip() == '':
        return default

    return [e for e in raw.split('\n') if e is not None and e.strip() != '']


def jinja2_settings(settings):
    settings.setdefault('jinja2.i18n.domain', 'eduid-dashboard')
    settings.setdefault('jinja2.newstyle', True)

    settings.setdefault('jinja2.extensions', ['jinja2.ext.with_'])

    settings.setdefault('jinja2.directories', 'eduiddashboard:templates')
    settings.setdefault('jinja2.undefined', 'strict')
    settings.setdefault('jinja2.i18n.domain', 'eduid-dashboard')
    settings.setdefault('jinja2.filters', """
        route_url = pyramid_jinja2.filters:route_url_filter
        static_url = pyramid_jinja2.filters:static_url_filter
        get_flash_message_text = eduiddashboard.filters:get_flash_message_text
        get_flash_message_type = eduiddashboard.filters:get_flash_message_type
        address_type_text = eduiddashboard.filters:address_type_text
        country_name = eduiddashboard.filters:country_name
        context_route_url = eduiddashboard.filters:context_route_url
        safe_context_route_url = eduiddashboard.filters:safe_context_route_url
    """)


def add_custom_deform_templates_path():
    templates_path = 'templates/form-widgets'
    try:
        path = resource_filename('eduiddashboard', templates_path)
    except ImportError:
        from os.path import dirname, join
        path = join(dirname(__file__), templates_path)

    loader = Form.default_renderer.loader
    loader.search_path = (path, ) + loader.search_path


def add_custom_workmode_templates_path(workmode='personal'):
    if workmode != 'personal':

        templates_path = 'templates/{0}'.format(workmode)
        try:
            path = resource_filename('eduiddashboard', templates_path)
        except ImportError:
            from os.path import dirname, join
            path = join(dirname(__file__), templates_path)

        loader = Form.default_renderer.loader
        loader.search_path = (path, ) + loader.search_path


def profile_urls(config):
    config.add_route('profile-editor', '/', factory=PersonFactory)
    config.add_route('personaldata', '/personaldata/',
                     factory=PersonFactory)
    config.add_route('emails', '/emails/',
                     factory=PersonFactory)
    config.add_route('emails-actions', '/emails-actions/',
                     factory=PersonFactory)
    config.add_route('security', '/security/',
                     factory=SecurityFactory)
    config.add_route('reset-password', '/reset-password/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-expired', '/reset-password-expired/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-sent', '/reset-password/sent/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-email', '/reset-password/email/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-mina', '/reset-password/mina/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-step2', '/reset-password/{code}/',
                     factory=ResetPasswordFactory)
    # config.add_route('postaladdress', '/postaladdress/',
    #                  factory=PostalAddressFactory)
    config.add_route('mobiles', '/mobiles/',
                     factory=MobilesFactory)
    config.add_route('mobiles-actions', '/mobiles-actions/',
                     factory=MobilesFactory)
    config.add_route('permissions', '/permissions/',
                     factory=PermissionsFactory)
    config.add_route('nins', '/nins/',
                     factory=NinsFactory)
    config.add_route('nins-actions', '/nins-actions/',
                     factory=NinsFactory)

    config.add_route('userstatus', '/userstatus/',
                     factory=StatusFactory)

    # wizard routes
    config.add_route('wizard-nins', '/nin-wizard/',
                     factory=NinsFactory)


def admin_urls(config):
    config.add_route('admin-status', '/status/', factory=AdminFactory)


def disabled_admin_urls(config):
    config.add_route('admin-status', '/status/', factory=ForbiddenFactory)


def includeme(config):
    # DB setup
    settings = config.registry.settings
    mongo_replicaset = settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        mongodb = MongoDB(db_uri=settings['mongo_uri'],
                          replicaSet=mongo_replicaset)
        authninfodb = MongoDB(db_uri=settings['mongo_uri_authninfo'],
                              replicaSet=mongo_replicaset)
    else:
        mongodb = MongoDB(db_uri=settings['mongo_uri'])
        authninfodb = MongoDB(db_uri=settings['mongo_uri_authninfo'])

    config.registry.settings['mongodb'] = mongodb
    config.registry.settings['authninfodb'] = authninfodb
    config.registry.settings['db_conn'] = mongodb.get_connection

    config.set_request_property(lambda x: x.registry.settings['mongodb'].get_database(), 'db', reify=True)
    config.set_request_property(lambda x: x.registry.settings['authninfodb'].get_database(), 'authninfodb', reify=True)

    # Create userdb instance and store it in our config,
    # and make a getter lambda for pyramid to retreive it
    _userdb = UserDB(config.registry.settings)
    config.registry.settings['userdb'] = _userdb
    config.add_request_method(lambda x: x.registry.settings['userdb'], 'userdb', reify=True)

    msgrelay = MsgRelay(config.registry.settings)
    config.registry.settings['msgrelay'] = msgrelay
    config.add_request_method(get_msgrelay, 'msgrelay', reify=True)

    config.set_request_property(is_logged, 'is_logged', reify=True)

    config.add_route('home', '/', factory=HomeFactory)
    if settings['workmode'] == 'personal':
        config.include(profile_urls, route_prefix='/profile/')
        config.include(disabled_admin_urls, route_prefix='/admin/{userid}/')
    else:
        config.include(profile_urls, route_prefix='/users/{userid}/')
        config.include(admin_urls, route_prefix='/admin/{userid}/')

    config.add_route('token-login', '/tokenlogin/')
    if settings['workmode'] == 'personal':
        config.add_route('verifications',
                         '/verificate/{model}/{code}/',
                         factory=VerificationsFactory)
    else:
        config.add_route('verifications',
                         '/verificate/{model}/{code}/',
                         factory=ForbiddenFactory)
    config.add_route('help', '/help/', factory=HelpFactory)
    config.add_route('session-reload', '/session-reload/',
                     factory=PersonFactory)

    config.add_route('set_language', '/set_language/')
    config.add_route('error500test', '/error500test/')
    config.add_route('error500', '/error500/')

    config.add_route('error404', '/error404/')

    if not settings.get('testing', False):
        config.add_view(context=Exception,
                        view='eduiddashboard.views.portal.exception_view',
                        renderer='templates/error500.jinja2')
        config.add_view(context=HTTPNotFound,
                        view='eduiddashboard.views.portal.not_found_view',
                        renderer='templates/error404.jinja2')

    # Favicon
    config.add_route('favicon', '/favicon.ico')
    config.add_view('eduiddashboard.views.static.favicon_view', route_name='favicon')


def main(global_config, **settings):
    """ This function returns a WSGI application.

    It is usually called by the PasteDeploy framework during
    ``paster serve``.
    """
    settings = dict(settings)

    # read pyramid_mailer options
    for key, default in (
        ('host', 'localhost'),
        ('port', '25'),
        ('username', None),
        ('password', None),
        ('default_sender', 'no-reply@example.com')
    ):
        option = 'mail.' + key
        settings[option] = read_setting_from_env(settings, option, default)

    # Parse settings before creating the configurator object
    available_languages = read_mapping(settings, 'available_languages',
                                       default={'en': 'English',
                                                'sv': 'Svenska'})

    settings['lang_cookie_domain'] = read_setting_from_env(settings,
                                                           'lang_cookie_domain',
                                                           None)

    settings['lang_cookie_name'] = read_setting_from_env(settings,
                                                         'lang_cookie_name',
                                                         'lang')

    for item in (
        'mongo_uri',
        'site.name',
        'auth_shared_secret',
        'mongo_uri_am',
        'mongo_uri_authninfo',
        'personal_dashboard_base_url',
        'vccs_url',
        'nin_service_name',
        'nin_service_url',
    ):
        settings[item] = read_setting_from_env(settings, item, None)
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    mongo_replicaset = read_setting_from_env(settings, 'mongo_replicaset',
                                             None)
    if mongo_replicaset is not None:
        settings['mongo_replicaset'] = mongo_replicaset

    # configure Celery broker
    broker_url = read_setting_from_env(settings, 'broker_url', 'amqp://')
    celery.conf.update(BROKER_URL=broker_url)
    settings['celery'] = celery
    settings['broker_url'] = broker_url

    settings['msg_broker_url'] = read_setting_from_env(settings,
                                                       'msg_broker_url',
                                                       'amqp://eduid_msg')

    settings['workmode'] = read_setting_from_env(settings, 'workmode',
                                                 'personal')

    if settings['workmode'] not in AVAILABLE_WORK_MODES:
        raise ConfigurationError(
            'The workmode {0} is not in available work modes'.format(
                settings['workmode'])
        )

    settings['permissions_mapping'] = read_mapping(
        settings,
        'permissions_mapping',
        available_keys=AVAILABLE_WORK_MODES,
        default=REQUIRED_GROUP_PER_WORKMODE
    )

    settings['available_permissions'] = read_list(
        settings,
        'available_permissions',
        default=AVAILABLE_PERMISSIONS)

    settings['required_loa'] = read_mapping(
        settings,
        'required_loa',
        available_keys=AVAILABLE_LOA_LEVEL,
        default=REQUIRED_LOA_PER_WORKMODE,
    )

    settings['available_loa'] = read_list(
        settings,
        'available_loa',
        default=AVAILABLE_LOA_LEVEL)

    settings['enable_postal_address_retrieve'] = read_setting_from_env(
        settings, 'enable_postal_address_retrieve', True
    )

    try:
        settings['session.expire'] = int(settings.get('session.expire', 3600))
    except ValueError:
        raise ConfigurationError('session.expire should be a valid integer')

    try:
        settings['session.timeout'] = int(settings.get(
            'session.timeout',
            settings['session.expire'])
        )
    except ValueError:
        raise ConfigurationError('session.expire should be a valid integer')

    settings['session.key'] = read_setting_from_env(settings, 'session.key',
                                                    'session')

    settings['groups_callback'] = read_setting_from_env(settings,
                                                        'groups_callback',
                                                        groups_callback)

    settings['available_languages'] = available_languages

    settings['default_country_code'] = read_setting_from_env(
        settings,
        'default_country_code',
        '+46',  # sweden country code
    )

    settings['default_country_location'] = read_setting_from_env(
        settings,
        'default_country_location',
        'SE',  # sweden country code
    )

    settings['verification_code_timeout'] = read_setting_from_env(
        settings,
        'verification_code_timeout',
        '30',
    )

    settings['password_length'] = read_setting_from_env(
        settings,
        'password_length',
        '12',
    )

    settings['password_entropy'] = read_setting_from_env(
        settings,
        'password_entropy',
        '60',
    )

    jinja2_settings(settings)

    config = Configurator(settings=settings,
                          root_factory=RootFactory,
                          locale_negotiator=locale_negotiator)

    config.set_request_property(get_locale_name, 'locale', reify=True)

    locale_path = read_setting_from_env(settings, 'locale_dirs',
                                        'eduiddashboard:locale')
    config.add_translation_dirs(locale_path)

    config.include('pyramid_beaker')
    config.include('pyramid_jinja2')
    config.include('deform_bootstrap')
    config.include('pyramid_deform')

    if 'development' in settings and asbool(settings['development']):
        pass
    else:
        config.include('eduiddashboard.saml2')

    if 'testing' in settings and asbool(settings['testing']):
        config.include('pyramid_mailer.testing')
    else:
        config.include('pyramid_mailer')

    config.include('pyramid_tm')

    add_custom_deform_templates_path()
    add_custom_workmode_templates_path()

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('deform', 'deform:static',
                           cache_max_age=3600)
    config.add_static_view('deform_bootstrap', 'deform_bootstrap:static',
                           cache_max_age=3600)

    # eudid specific configuration
    includeme(config)

    if 'development' in settings and asbool(settings['development']):
        from eduiddashboard.development import auth as local_auth
        config = local_auth.setup_auth(config)
        config.scan(ignore=[re.compile('.*test(s|ing).*').search, 'eduiddashboard.saml2'])
    else:
        config.scan(ignore=[re.compile('.*test(s|ing).*').search, 'eduiddashboard.development'])
    return config.make_wsgi_app()
