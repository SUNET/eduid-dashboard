import os
from datetime import datetime, timedelta

from eduid_common.session import SessionObject

from pyramid.interfaces import ISession
from pyramid.settings import asbool
from zope.interface import implementer

from binascii import hexlify


def EduIDSessionFactoryConfig(**options):
    """ Return a Pyramid session factory using eduid session settings
    supplied directly as ``**options``"""

    class PyramidEduidSessionObject(SessionObject):
        _options = options
        _cookie_on_exception = _options.pop('cookie_on_exception', True)
        _constant_csrf_token = _options.pop('constant_csrf_token', False)

        def __init__(self, request):
            SessionObject.__init__(self, request.environ, **self._options)
            def session_callback(request, response):
                exception = getattr(request, 'exception', None)
                if (
                    (exception is None or self._cookie_on_exception)
                    and self.accessed()
                ):
                    self.persist()
                    headers = self.__dict__['_headers']
                    if headers['set_cookie'] and headers['cookie_out']:
                        response.headerlist.append(
                            ('Set-Cookie', headers['cookie_out']))
            request.add_response_callback(session_callback)

        # ISession API

        @property
        def new(self):
            return self.last_accessed is None

        changed = SessionObject.save

        # modifying dictionary methods

        def clear(self):
            return self._session().clear()

        def update(self, d, **kw):
            return self._session().update(d, **kw)

        def setdefault(self, k, d=None):
            return self._session().setdefault(k, d)

        def pop(self, k, d=None):
            return self._session().pop(k, d)

        def popitem(self):
            return self._session().popitem()

        # Flash API methods
        def flash(self, msg, queue='', allow_duplicate=True):
            storage = self.setdefault('_f_' + queue, [])
            if allow_duplicate or (msg not in storage):
                storage.append(msg)

        def pop_flash(self, queue=''):
            storage = self.pop('_f_' + queue, [])
            return storage

        def peek_flash(self, queue=''):
            storage = self.get('_f_' + queue, [])
            return storage

        # CSRF API methods
        def new_csrf_token(self):
            token = (self._constant_csrf_token
                     or hexlify(os.urandom(20)).decode('ascii'))
            self['_csrft_'] = token
            return token

        def get_csrf_token(self):
            token = self.get('_csrft_', None)
            if token is None:
                token = self.new_csrf_token()
            return token

    return implementer(ISession)(PyramidEduidSessionObject)


def session_factory_from_settings(settings):
    """ Return a Pyramid session factory using settings
    supplied from a Paste configuration file"""
    prefix = 'session.'
    options = {}

    for k, v in settings.items():
        if k.startswith(prefix):
            option_name = k[len(prefix):]
            if option_name == 'cookie_on_exception':
                v = asbool(v)
            options[option_name] = v

    options = coerce_session_params(options)
    return EduIDSessionFactoryConfig(**options)


def coerce_session_params(params):
    rules = [
        ('data_dir', (str, NoneType), "data_dir must be a string "
         "referring to a directory."),
        ('lock_dir', (str, NoneType), "lock_dir must be a string referring to a "
         "directory."),
        ('type', (str, NoneType), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta, int), "Cookie expires was "
         "not a boolean, datetime, int, or timedelta instance."),
        ('cookie_domain', (str, NoneType), "Cookie domain must be a "
         "string."),
        ('cookie_path', (str, NoneType), "Cookie path must be a "
         "string."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str, NoneType), "Session secret must be a string."),
        ('validate_key', (str, NoneType), "Session encrypt_key must be "
         "a string."),
        ('encrypt_key', (str, NoneType), "Session validate_key must be "
         "a string."),
        ('secure', (bool, NoneType), "Session secure must be a boolean."),
        ('httponly', (bool, NoneType), "Session httponly must be a boolean."),
        ('timeout', (int, NoneType), "Session timeout must be an "
         "integer."),
        ('auto', (bool, NoneType), "Session is created if accessed."),
        ('webtest_varname', (str, NoneType), "Session varname must be "
         "a string."),
    ]
    opts = verify_rules(params, rules)
    cookie_expires = opts.get('cookie_expires')
    if cookie_expires and isinstance(cookie_expires, int) and \
       not isinstance(cookie_expires, bool):
        opts['cookie_expires'] = timedelta(seconds=cookie_expires)
    return opts


def verify_rules(params, ruleset):
    for key, types, message in ruleset:
        if key in params:
            params[key] = verify_options(params[key], types, message)
    return params


def verify_options(opt, types, error):
    if not isinstance(opt, types):
        if not isinstance(types, tuple):
            types = (types,)
        coerced = False
        for typ in types:
            try:
                if typ in (list, tuple):
                    opt = [x.strip() for x in opt.split(',')]
                else:
                    if typ == bool:
                        typ = asbool
                    elif typ == int:
                        typ = asint
                    elif typ in (timedelta, datetime):
                        if not isinstance(opt, typ):
                            raise Exception("%s requires a timedelta type", typ)
                    opt = typ(opt)
                coerced = True
            except:
                pass
            if coerced:
                break
        if not coerced:
            raise Exception(error)
    elif isinstance(opt, str) and not opt.strip():
        raise Exception("Empty strings are invalid for: %s" % error)
    return opt


def includeme(config):
    session_factory = session_factory_from_settings(config.registry.settings)
    config.set_session_factory(session_factory)
