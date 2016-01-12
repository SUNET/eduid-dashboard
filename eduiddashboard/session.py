
import os, binascii
from time import time
import collections
from pyramid.interfaces import ISessionFactory, ISession
from eduid_common.sessions.session import SessionManager,


@implementer(ISessionFactory)
class SessionFactory(object):

    def __init__(self, settings):
        redis_uri = settings['redis_uri']
        self.manager = SessionManager(redis_uri)

    def __call__(self, request):
        settings = request.registry.settings
        session_name = settings.get('session_id_name', 'sessid')
        cookies = request.cookies
        token = cookies.get(session_name, None)
        if token is not None:
            base_session = self.manager.get_session(token=token)
            new = False
        else:
            base_session = self.manager.get_session(data={})
            base_session['flash_messages'] = {'default': []}
            base_session.commit()
            token = base_session.token
            request.response.set_cookie(
                    name=session_name,
                    value=base_session.token,
                    secure=True,
                    httponly=True
                    )
            new = True
        return Session(base_session, new)


@implementer(ISession)
class Session(collections.MutableMapping):

    def __init__(self, base_session, new):
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
        self._changed = True

    def flash(self, msg, queue='', allow_duplicate=True):
        if not queue:
            queue = 'default'
        if not allow_duplicate:
            if msg in self._session['flash_messages'][queue]:
                return
        self._session['flash_messages'][queue].append(msg)
        self._session.commit()

    def pop_flash(queue=''):
        if not queue:
            queue = 'default'
        if queue in self:
            msgs = self.pop(queue)
            self._session.commit()
            return msgs
        return []

    def peek_flash(queue=''):
        if not queue:
            queue = 'default'
        return self.get(queue, [])

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
