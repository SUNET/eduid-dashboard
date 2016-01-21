
import os, binascii
from time import time
import collections
from zope.interface import implementer
from pyramid.interfaces import ISessionFactory, ISession
from eduid_common.session.session import SessionManager

import logging
logger = logging.getLogger(__name__)


@implementer(ISessionFactory)
class SessionFactory(object):

    def __init__(self, settings):
        redis_host = settings['redis_host']
        redis_port = settings['redis_port']
        redis_db = settings['redis_db']
        self.manager = SessionManager(redis_host, redis_port, redis_db)

    def __call__(self, request):
        self.request = request
        settings = request.registry.settings
        session_name = settings.get('session.key', 'session')
        secret = settings.get('session.secret')
        cookies = request.cookies
        token = cookies.get(session_name, None)
        if token is not None:
            base_session = self.manager.get_session(token=token, secret=secret)
            new = False
        else:
            base_session = self.manager.get_session(data={}, secret=secret)
            base_session['flash_messages'] = {'default': []}
            base_session.commit()
            token = base_session.token
            domain = settings.get('session.domain')
            new = True
            def set_cookie_callback(request, response):
                response.set_cookie(
                        name=session_name,
                        value=token,
                        domain=domain,
                        #secure=True,
                        #httponly=True
                        )
                self.request = None
                return True
            self.request.add_response_callback(set_cookie_callback)
        return Session(request, base_session, new)


@implementer(ISession)
class Session(collections.MutableMapping):

    _dirty = False

    def __init__(self, request, base_session, new):
        self.request = request
        self._session = base_session
        self._created = time()
        self._new = new
        self._changed = False

    def __getitem__(self, key, default=None):
        return self._session.__getitem__(key, default=None)

    def __setitem__(self, key, value):
        self._session[key] = value
        self._session.commit()

    def __delitem__(self, key):
        del self._session[key]
        self._session.commit()

    def __iter__(self):
        return self._session.__iter__()

    def __len__(self):
        return len(self._session)

    def __contains__(self, key):
        return self._session.__contains__(key)

    @property
    def created(self):
        return self._created

    @property
    def new(self):
        return self._new

    def invalidate(self):
        pass

    def changed(self):
        pass

    def flash(self, msg, queue='', allow_duplicate=True):
        if not queue:
            queue = 'default'
        elif queue not in self._session['flash_messages']:
            self._session['flash_messages'][queue] = []
        if not allow_duplicate:
            if msg in self._session['flash_messages'][queue]:
                return
        self._session['flash_messages'][queue].append(msg)
        self._session.commit()

    def pop_flash(self, queue=''):
        if not queue:
            queue = 'default'
        if queue in self._session['flash_messages']:
            msgs = self._session['flash_messages'].pop(queue)
            self._session.commit()
            return msgs
        return []

    def peek_flash(self, queue=''):
        if not queue:
            queue = 'default'
        return self._session['flash_messages'].get(queue, [])

    def new_csrf_token(self):
        token = binascii.hexlify(os.urandom(20))
        self['_csrft_'] = token
        self._session.commit()
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        return token

    def persist(self):
        self._session.commit()
