#!/opt/eduid/bin/python
# -*- coding: utf-8 -*-

import sys
import pprint
from pyramid.paster import bootstrap

from eduid_common.session.session import SessionManager
from eduiddashboard.session import _get_user_by_eppn

import logging
logger = logging.getLogger(__name__)

__author__ = 'ft'

"""
Ask the attribute manager to sync a user.
"""

default_config_file = '/opt/eduid/eduid-dashboard/etc/eduid-dashboard.ini'


def main(eppn):
    env = bootstrap(default_config_file)
    settings = env['request'].registry.settings

    user = _get_user_by_eppn(env['request'], eppn, legacy_user=False)
    print('Requesting Attribute Manager sync of user {} from the dashboard application'.format(user))

    res = env['request'].amrelay.request_sync(user)

    print('Result of reqest_sync: {}'.format(res))

    return True

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            print('Syntax: amsync_eppn.py eppn')
            sys.exit(1)
        res = main(sys.argv[1])
        if res:
            sys.exit(0)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
