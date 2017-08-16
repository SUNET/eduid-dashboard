# -*- coding: utf-8 -*-

import sys
import pprint
from pyramid.paster import bootstrap

from eduid_common.session.session import SessionManager

import logging
logger = logging.getLogger(__name__)

__author__ = 'ft'

"""
Read and decode a session from Redis. Supply the token (id starting with lower-case 'a')
from an existing session.
"""

default_config_file = '/opt/eduid/eduid-dashboard/etc/eduid-dashboard.ini'


def main(token):
    env = bootstrap(default_config_file)
    settings = env['request'].registry.settings
    secret = settings.get('session.secret')
    manager = SessionManager(cfg = settings, ttl = 3600, secret = secret)
    session = manager.get_session(token = token)
    print('Session: {}'.format(session))
    print('Data:\n{}'.format(pprint.pformat(dict(session))))
    return True

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            print('Syntax: decode_session.py aTOKEN')
            sys.exit(1)
        res = main(sys.argv[1])
        if res:
            sys.exit(0)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
