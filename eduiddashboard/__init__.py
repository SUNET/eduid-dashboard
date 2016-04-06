import re

import logging

from pkg_resources import resource_filename
from deform import Form

from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPNotFound
from pyramid.settings import asbool
from pyramid.i18n import get_locale_name

from eduid_userdb import MongoDB, UserDB
from eduid_userdb.dashboard import UserDBWrapper, DashboardUserDB
from eduid_common.config.parsers import IniConfigParser
from eduiddashboard.i18n import locale_negotiator
from eduiddashboard.permissions import (RootFactory, PersonFactory,
                                        SecurityFactory, ResetPasswordFactory,
                                        PostalAddressFactory, MobilesFactory,
                                        PermissionsFactory, StatusFactory,
                                        VerificationsFactory, HomeFactory,
                                        NinsFactory, ForbiddenFactory,
                                        HelpFactory, AdminFactory, is_logged)

from eduiddashboard.session import SessionFactory
from eduiddashboard.msgrelay import MsgRelay
from eduiddashboard.lookuprelay import LookupMobileRelay
from eduiddashboard.idproofinglog import IDProofingLog
from eduiddashboard.amrelay import AmRelay
from eduiddashboard.stats import get_stats_instance
import eduiddashboard.loa


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
    config.add_route('reset-password-mobile', '/reset-password/mobile/',
                     factory=ResetPasswordFactory)
    config.add_route('reset-password-mobile2', '/reset-password/mobile/{code}/',
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

    config.add_route('terminate-account', '/terminate-account/',
                     factory=PersonFactory)
    config.add_route('account-terminated', '/account-terminated/',
                     factory=RootFactory)

    config.add_route('start-password-change', '/start-password-change/',
                     factory=SecurityFactory)
    config.add_route('password-change', '/password-change/',
                     factory=SecurityFactory)

    config.add_route('nins-verification-chooser',
                     '/nins-verification-chooser/',
                     factory=NinsFactory)


def admin_urls(config):
    config.add_route('admin-status', '/status/', factory=AdminFactory)


def disabled_admin_urls(config):
    config.add_route('admin-status', '/status/', factory=ForbiddenFactory)


def includeme(config):
    # DB setup
    settings = config.registry.settings
    mongodb = MongoDB(db_uri=settings['mongo_uri'])
    authninfodb = MongoDB(db_uri=settings['mongo_uri'])

    config.registry.settings['mongodb'] = mongodb
    config.registry.settings['authninfodb'] = authninfodb
    config.registry.settings['db_conn'] = mongodb.get_connection

    config.set_request_property(lambda x: x.registry.settings['mongodb'].get_database('eduid_dashboard'),
                                'db', reify=True)
    config.set_request_property(lambda x: x.registry.settings['authninfodb'].get_database('eduid_idp_authninfo'),
                                'authninfodb', reify=True)

    # Create userdb instance and store it in our config,
    # and make a getter lambda for pyramid to retreive it
    _userdb = UserDBWrapper(config.registry.settings['mongo_uri'])
    config.registry.settings['userdb'] = _userdb
    config.add_request_method(lambda x: x.registry.settings['userdb'], 'userdb', reify=True)

    # same DB using new style users
    config.registry.settings['userdb_new'] = UserDB(config.registry.settings['mongo_uri'], db_name='eduid_am')
    config.add_request_method(lambda x: x.registry.settings['userdb_new'], 'userdb_new', reify=True)

    # Set up handle to Dashboards private UserDb (DashboardUserDB)
    _dashboard_userdb = DashboardUserDB(config.registry.settings['mongo_uri'])
    config.registry.settings['dashboard_userdb'] = _dashboard_userdb
    config.add_request_method(lambda x: x.registry.settings['dashboard_userdb'], 'dashboard_userdb', reify=True)

    config.registry.settings['msgrelay'] = MsgRelay(config.registry.settings)
    config.add_request_method(lambda x: x.registry.settings['msgrelay'], 'msgrelay', reify=True)

    config.registry.settings['lookuprelay'] = LookupMobileRelay(config.registry.settings)
    config.add_request_method(lambda x: x.registry.settings['lookuprelay'], 'lookuprelay', reify=True)

    config.registry.settings['idproofinglog'] = IDProofingLog(config.registry.settings)
    config.add_request_method(lambda x: x.registry.settings['idproofinglog'], 'idproofinglog', reify=True)

    config.registry.settings['amrelay'] = AmRelay(config.registry.settings)
    config.add_request_method(lambda x: x.registry.settings['amrelay'], 'amrelay', reify=True)

    config.set_request_property(is_logged, 'is_logged', reify=True)

    config.registry.settings['stats'] = get_stats_instance(settings, log)
    # Make the result of the lambda available as request.stats
    config.set_request_property(lambda x: x.registry.settings['stats'], 'stats', reify=True)

    #
    # Route setups
    #
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
    # Seems unused -- ft@ 2016-01-14
    #config.add_route('session-reload', '/session-reload/',
    #                 factory=PersonFactory)

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
    cp = IniConfigParser('')  # We don't need to provide the settings file as it is already loaded

    settings['developer_mode'] = cp.read_setting_from_env_bool(settings,
                                                               'developer_mode',
                                                               default=False)

    # read pyramid_mailer options
    for key, default in (
            ('host', 'localhost'),
            ('port', '25'),
            ('username', None),
            ('password', None),
            ('default_sender', 'no-reply@example.com'),
            ('support_email', 'support@eduid.se')
    ):
        option = 'mail.' + key
        settings[option] = cp.read_setting_from_env(settings, option, default)

    # Parse settings before creating the configurator object
    available_languages = cp.read_mapping(settings, 'available_languages',
                                          default={'en': 'English',
                                                   'sv': 'Svenska'})

    settings['lang_cookie_domain'] = cp.read_setting_from_env(settings,
                                                              'lang_cookie_domain',
                                                              None)

    settings['lang_cookie_name'] = cp.read_setting_from_env(settings,
                                                            'lang_cookie_name',
                                                            'lang')

    settings['enable_mm_verification'] = cp.read_setting_from_env_bool(settings,
                                                                       'enable_mm_verification',
                                                                       default=True)

    required_settings = (
        'mongo_uri',
        'site.name',
        'dashboard_hostname',
        'dashboard_baseurl',
        'auth_shared_secret',
        'personal_dashboard_base_url',
        'signup_base_url',
        'vccs_url',
        'mobile_service_name',
        'letter_service_url',
        )
    if settings['enable_mm_verification']:
        required_settings += (
            'nin_service_name',
            'nin_service_url',
            )

    for item in required_settings:
        settings[item] = cp.read_setting_from_env(settings, item, None)
        if settings[item] is None:
            raise ConfigurationError(
                'The {0} configuration option is required'.format(item))

    # configuration for Celery brokers
    default_celery_conf = {
        'BROKER_URL': None,  # The broker url needs to be set when instantiating the broker
        'MONGO_URI': settings.get('mongo_uri'),
        'CELERY_TASK_SERIALIZER': 'json',
        'CELERY_RESULT_BACKEND': 'amqp',
        # Avoid broken connections across firewall by disabling pool
        # http://docs.celeryproject.org/en/latest/configuration.html#broker-pool-limit
        'BROKER_POOL_LIMIT': 0,
    }
    settings['default_celery_conf'] = default_celery_conf
    settings['am_broker_url'] = cp.read_setting_from_env(settings, 'broker_url', 'amqp://')
    settings['msg_broker_url'] = cp.read_setting_from_env(settings, 'msg_broker_url', 'amqp://eduid_msg')
    settings['lookup_mobile_broker_url'] = cp.read_setting_from_env(settings, 'lookup_mobile_broker_url',
                                                                    'amqp://lookup_mobile')

    settings['workmode'] = cp.read_setting_from_env(settings, 'workmode',
                                                    'personal')

    if settings['workmode'] not in AVAILABLE_WORK_MODES:
        raise ConfigurationError(
            'The workmode {0} is not in available work modes'.format(
                settings['workmode'])
        )

    settings['permissions_mapping'] = cp.read_mapping(
        settings,
        'permissions_mapping',
        available_keys=AVAILABLE_WORK_MODES,
        default=REQUIRED_GROUP_PER_WORKMODE
    )

    settings['available_permissions'] = cp.read_list(
        settings,
        'available_permissions',
        default=AVAILABLE_PERMISSIONS)

    settings['required_loa'] = cp.read_mapping(
        settings,
        'required_loa',
        available_keys=eduiddashboard.loa.AVAILABLE_LOA_LEVEL,
        default=REQUIRED_LOA_PER_WORKMODE,
    )

    settings['available_loa'] = cp.read_list(
        settings,
        'available_loa',
        default=eduiddashboard.loa.AVAILABLE_LOA_LEVEL)

    settings['enable_postal_address_retrieve'] = cp.read_setting_from_env_bool(
        settings, 'enable_postal_address_retrieve', True
    )

    try:
        settings['session.cookie_max_age'] = int(settings.get('session.cookie_max_age', 600))
    except ValueError:
        raise ConfigurationError('session.cookie_max_age should be a valid integer')

    try:
        settings['session.timeout'] = int(settings.get(
            'session.timeout',
            settings['session.cookie_max_age'])
        )
    except ValueError:
        raise ConfigurationError('session.timeout should be a valid integer')

    settings['session.cookie_domain'] = cp.read_setting_from_env(settings, 'session.cookie_domain',
                                                                 'dashboard.docker')

    settings['session.cookie_path'] = cp.read_setting_from_env(settings, 'session.cookie_path',
                                                               '/')

    settings['session.cookie_httponly'] = cp.read_setting_from_env_bool(settings, 'session.cookie_httponly',
                                                                        'true')

    settings['session.cookie_secure'] = cp.read_setting_from_env_bool(settings, 'session.cookie_secure',
                                                                      'false')

    settings['session.key'] = cp.read_setting_from_env(settings, 'session.key',
                                                       'sessid')

    settings['session.secret'] = cp.read_setting_from_env(settings,
                                                          'session.secret')

    settings['REDIS_HOST'] = cp.read_setting_from_env(settings, 'redis_host',
                                                      'redis.docker')

    settings['REDIS_PORT'] = int(cp.read_setting_from_env(settings, 'redis_port',
                                                          6379))

    settings['REDIS_DB'] = int(cp.read_setting_from_env(settings, 'redis_db', 0))

    settings['REDIS_SENTINEL_HOSTS'] = cp.read_list(
        settings,
        'redis_sentinel_hosts',
        default=[])
    settings['REDIS_SENTINEL_SERVICE_NAME'] = cp.read_setting_from_env(settings, 'redis_sentinel_service_name',
                                                                       'redis-cluster')

    settings['groups_callback'] = cp.read_setting_from_env(settings,
                                                           'groups_callback',
                                                           groups_callback)

    settings['available_languages'] = available_languages

    settings['default_country_code'] = cp.read_setting_from_env(
        settings,
        'default_country_code',
        '+46',  # sweden country code
    )

    settings['default_country_location'] = cp.read_setting_from_env(
        settings,
        'default_country_location',
        'SE',  # sweden country code
    )

    settings['verification_code_timeout'] = cp.read_setting_from_env(
        settings,
        'verification_code_timeout',
        '30',
    )

    settings['password_length'] = cp.read_setting_from_env(
        settings,
        'password_length',
        '12',
    )

    settings['password_entropy'] = cp.read_setting_from_env(
        settings,
        'password_entropy',
        '60',
    )

    settings['stathat_username'] = cp.read_setting_from_env(settings, 'stathat_username')

    jinja2_settings(settings)

    config = Configurator(settings=settings,
                          root_factory=RootFactory,
                          locale_negotiator=locale_negotiator)

    config.add_tween('eduiddashboard.middleware.reauthn_ts_tween_factory')

    config.set_request_property(get_locale_name, 'locale', reify=True)

    locale_path = cp.read_setting_from_env(settings, 'locale_dirs',
                                           'eduiddashboard:locale')
    config.add_translation_dirs(locale_path)

    factory = SessionFactory(settings)
    config.set_session_factory(factory)

    config.include('pyramid_jinja2')
    config.include('deform_bootstrap')
    config.include('pyramid_deform')

    config.include('eduiddashboard.saml2')

    if settings['developer_mode'] or ('testing' in settings and asbool(settings['testing'])):
        config.include('pyramid_mailer.testing')
    else:
        config.include('pyramid_mailer')

    config.include('pyramid_tm')

    add_custom_deform_templates_path()
    add_custom_workmode_templates_path()

    if settings.get('static_url', False):
        config.add_static_view(settings['static_url'], 'static')
    else:
        config.add_static_view('static', 'static', cache_max_age=3600)

    # eudid specific configuration
    includeme(config)

    config.scan(ignore=[re.compile('.*test(s|ing).*').search, 'eduiddashboard.development'])
    return config.make_wsgi_app()
