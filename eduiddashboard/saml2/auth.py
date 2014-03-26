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
from eduiddashboard.saml2.utils import get_SAML_attribute

logger = logging.getLogger(__name__)


def get_authn_ctx(session_info):
    """
    Get the SAML2 AuthnContext of the currently logged in users session.

    session_info is a dict like

        {'authn_info': [('http://www.swamid.se/policy/assurance/al1',
                    ['https://dev.idp.eduid.se/idp.xml'])],
         ...
        }

    :param session_info: The SAML2 session_info
    :return: The first AuthnContext
    :rtype: string | None
    """
    try:
        return session_info['authn_info'][0][0]
    except KeyError:
        return None


def get_loa(available_loa, session_info):
    """
    Get the Assurance Level of the currently logged in users session.

    The difference between this and AuthnContext is that this function
    makes sure the returned value is known to this application.

    :param available_loa: List of permissible values. First one is default.
    :param session_info: The SAML2 session_info
    :return: The AL level

    :type available_loa: [string()]
    :type session_info: dict
    :rtype: string | None
    """
    if not available_loa:
        return AVAILABLE_LOA_LEVEL[0]

    default_loa = available_loa[0]

    if not session_info:
        return default_loa

    loa = get_authn_ctx(session_info)
    if loa in available_loa:
        return loa
    return default_loa


def authenticate(request, session_info):

    if session_info is None:
        raise TypeError('Session info is None')

    user_main_attribute = request.registry.settings.get(
        'saml2.user_main_attribute')

    attribute_values = get_SAML_attribute(session_info, user_main_attribute)
    if not attribute_values:
        logger.error('Could not find attribute {!r} in the SAML assertion'.format(user_main_attribute))
        return None

    saml_user = attribute_values[0]

    logger.debug('Retrieving existing user {!r} (from SAML attribute {!r})'.format(saml_user, user_main_attribute))
    try:
        user = request.userdb.get_user(saml_user)
        return user
    except request.userdb.exceptions.UserDoesNotExist:
        logger.error('The user "%s" does not exist' % saml_user)
    except request.userdb.exceptions.MultipleUsersReturned:
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
    if request.session is not None:
        request.session.delete()
    headers = forget(request)
    return headers
