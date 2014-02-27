# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from eduiddashboard.db import MongoDB
from pyramid.view import view_config

from eduiddashboard.i18n import TranslationString as _

import logging
logger = logging.getLogger(__name__)

# Uses the userid (user_main_attribute) for all fields except _id where
# the user objects _id in the same database will be used.
DATABASES = {
    'eduid_dashboard': [
        {'name': 'profiles', 'field': 'mail'},
        {'name': 'verifications', 'field': '_id'}
    ],
    'eduid_am': [
        {'name': 'attributes', 'field': 'mail'}
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
            for collection in dbs[dbname]['collections']:
                if collection['field'] == '_id':
                    pass
                else:
                    try:
                        hit = dbs[dbname]['db'][collection['name']].find({collection['field']: userid})[0]
                    except IndexError:
                        hit = {}
                    userdata[dbname][collection['name']] = hit


    return {
        'userdata': userdata,
        # DEBUG
        'dir_context': dir(context),
        'dir_request': dir(request)
    }