import os
import re

from pkg_resources import resource_filename
from deform import Form

from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool

from eduid_am.celery import celery
from eduiddashboard.db import MongoDB, get_db
from eduiddashboard.i18n import locale_negotiator
from eduiddashboard.permissions import RootFactory, PersonFactory
from eduiddashboard.saml2 import configure_authtk
from eduiddashboard.userdb import UserDB, get_userdb


def read_setting_from_env(settings, key, default=None):
    env_variable = key.upper()
    if env_variable in os.environ:
        return os.environ[env_variable]
    else:
        return settings.get(key, default)


def add_custom_deform_templates_path():
    templates_path = 'templates/form-widgets'
    try:
        path = resource_filename('eduiddashboard', templates_path)
    except ImportError:
        from os.path import dirname, join
        path = join(dirname(__file__), templates_path)

    loader = Form.default_renderer.loader
    loader.search_path = (path, ) + loader.search_path


def includeme(config):
    # DB setup
    mongo_replicaset = config.registry.settings.get('mongo_replicaset', None)
    if mongo_replicaset is not None:
        mongodb = MongoDB(config.registry.settings['mongo_uri'],
                          replicaSet=mongo_replicaset)
    else:
        mongodb = MongoDB(config.registry.settings['mongo_uri'])
    config.registry.settings['mongodb'] = mongodb
    config.registry.settings['db_conn'] = mongodb.get_connection

    config.set_request_property(get_db, 'db', reify=True)

    userdb = UserDB(config.registry.settings)
    config.registry.settings['userdb'] = userdb
    config.add_request_method(get_userdb, 'userdb', reify=True)

    # root views
    config.add_route('home', '/', factory=PersonFactory)
    config.add_route('help', '/help/')
    config.add_route('token-login', '/tokenlogin/')

    config.add_route('personaldata', '/personaldata/', factory=PersonFactory)
    config.add_route('emails', '/emails/', factory=PersonFactory)
    config.add_route('verifications',
                     '/verificate/{model}/{code}/',
                     factory=PersonFactory)


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
    available_languages = read_setting_from_env(settings,
                                                'available_languages',
                                                'en es')
    settings['available_languages'] = [
        lang for lang in available_languages.split(' ') if lang
    ]

    for item in (
        'mongo_uri',
        'site.name',
        'auth_shared_secret',
        'mongo_uri_am',
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

    settings.setdefault('jinja2.i18n.domain', 'eduid-dashboard')

    config = Configurator(settings=settings,
                          root_factory=RootFactory,
                          locale_negotiator=locale_negotiator)

    config = configure_authtk(config, settings)

    config.include('pyramid_beaker')
    config.include('pyramid_jinja2')
    config.include('deform_bootstrap')
    config.include('pyramid_deform')

    config.include('eduiddashboard.saml2')

    if 'testing' in settings and asbool(settings['testing']):
        config.include('pyramid_mailer.testing')
    else:
        config.include('pyramid_mailer')

    config.include('pyramid_tm')

    add_custom_deform_templates_path()

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('deform', 'deform:static',
                           cache_max_age=3600)
    config.add_static_view('deform_bootstrap', 'deform_bootstrap:static',
                           cache_max_age=3600)

    # eudid specific configuration
    includeme(config)

    config.scan(ignore=[re.compile('.*test(s|ing).*').search])
    return config.make_wsgi_app()
