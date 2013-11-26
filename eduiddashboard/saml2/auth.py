# This file was taken from https://bitbucket.org/lgs/pyramidsaml2/overview
# this was modified from django to pyramid.
#
# Copyright (C) 2010-2013 Yaco Sistemas (http://www.yaco.es)
# Copyright (C) 2009 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging

from pyramid.security import remember, forget

from eduiddashboard import AVAILABLE_LOA_LEVEL


logger = logging.getLogger(__name__)


def get_loa(available_loa, session_info):
    if available_loa:
        default_loa = available_loa[0]
    else:
        default_loa = AVAILABLE_LOA_LEVEL[0]

    if not session_info:
        return default_loa
    else:
        loa = session_info.get('ava', {}).get('eduPersonAssurance', [])
        if len(loa) > 0:
            loa = loa[0]
            if loa in available_loa:
                return loa
    return default_loa


def authenticate(request, session_info, attribute_mapping):

    if session_info is None or attribute_mapping is None:
        logger.error('Session info or attribute mapping are None')
        return None

    if not 'ava' in session_info:
        logger.error('"ava" key not found in session_info')
        return None

    attributes = session_info['ava']
    if not attributes:
        logger.error('The attributes dictionary is empty')

    user_main_attribute = request.registry.settings.get(
        'saml2.user_main_attribute')

    logger.debug('attributes: %s' % attributes)
    logger.debug('attribute_mapping: %s' % attribute_mapping)
    saml_user = None

    for saml_attr, local_fields in attribute_mapping.items():
        if (user_main_attribute in local_fields
                and saml_attr in attributes):
            saml_user = attributes[saml_attr][0]

    if saml_user is None:
        logger.error('Could not find saml_user value')
        return None

    user = None
    logger.debug('Retrieving existing user "%s"' % saml_user)
    try:
        user = request.userdb.get_user(saml_user)
        return user
    except request.userdb.UserDoesNotExist:
        logger.error('The user "%s" does not exist' % saml_user)
    except request.userdb.MultipleUsersReturned:
        logger.error("There are more than one user with %s = %s" %
                     (user_main_attribute, saml_user))


def login(request, session_info, user):
    main_attribute = request.registry.settings.get('saml2.user_main_attribute')
    request.session[main_attribute] = user[main_attribute]
    request.session['user'] = user
    request.session['eduPersonAssurance'] = get_loa(
        request.registry.settings.get('available_loa'),
        session_info
    )
    remember_headers = remember(request, user[main_attribute])
    return remember_headers


def logout(request):
    headers = forget(request)
    return headers
