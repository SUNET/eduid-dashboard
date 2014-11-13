# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from pyramid.view import view_config

from eduid_am.db import MongoDB
from eduiddashboard.i18n import TranslationString as _

import logging
logger = logging.getLogger(__name__)

# Uses the userid (user_main_attribute) for all fields except _id where
# the user objects _id in the same database will be used.
DATABASES = {
    'eduid_am': [
        {'name': 'attributes', 'field': 'mail'}
    ],
    'eduid_dashboard': [
        {'name': 'profiles', 'field': 'mail'},
        {'name': 'verifications', 'field': 'user_oid'}
    ],
    'eduid_signup': [
        {'name': 'registered', 'field': 'email'}
    ]
}


def get_databases():
    """
    Instantiates all databases from DATABASES

    {
        'eduid_am': {
            'collections': [{'collection': 'attributes', 'field': 'mail'}],
            'db': Database(MongoClient('localhost', 27017), u'eduid_am')},
        }, ...
    }
    :return dict with dbs and collection info
    """
    dbs = {}
    for item in DATABASES:
        dbs[item] = {
            'db': MongoDB().get_database(item),
            'collections': DATABASES[item]
        }
    return dbs


@view_config(route_name='admin-status', renderer='templates/admin/admin-status.jinja2',
             request_method='GET', permission='edit')
def admin_status(context, request):

    dbs = get_databases()
    userdata = {}

    userid = request.matchdict.get('userid', '')
    if userid:
        for dbname in dbs:
            userdata[dbname] = {}
            oid = None
            for collection in dbs[dbname]['collections']:
                try:
                    if collection['field'] == 'user_oid':
                        if oid:
                            hit = dbs[dbname]['db'][collection['name']].find({collection['field']: oid})[0]
                        else:
                            hit = {'error': 'No OID to look up.'}
                    else:
                        hit = dbs[dbname]['db'][collection['name']].find({collection['field']: userid})[0]
                        oid = hit['_id']
                except IndexError:
                    hit = {'error': 'No user found.'}
                userdata[dbname][collection['name']] = hit


    return {
        'userdata': userdata,
    }
