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


from pyramid.security import remember, forget

from eduiddashboard import AVAILABLE_LOA_LEVEL
from eduiddashboard.saml2.utils import get_saml_attribute

from eduiddashboard import log


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
    """
    Locate a user using the identity found in the SAML assertion.

    :param request: Request object
    :param session_info: Session info received by pysaml2 client

    :returns: User dict

    :type request: Request()
    :type session_info: dict()
    :rtype: dict() or None
    """
    if session_info is None:
        raise TypeError('Session info is None')

    user_main_attribute = request.registry.settings.get('saml2.user_main_attribute')

    attribute_values = get_saml_attribute(session_info, user_main_attribute)
    if not attribute_values:
        log.error('Could not find attribute {!r} in the SAML assertion'.format(user_main_attribute))
        return None

    saml_user = attribute_values[0]

    # If user_main_attribute is eduPersonPrincipalName, there value might be scoped
    # and the scope (e.g. "@example.com") might have to be removed before looking
    # for the user in the database.
    strip_suffix = request.registry.settings.get('saml2.strip_saml_user_suffix')
    if strip_suffix:
        if saml_user.endswith(strip_suffix):
            saml_user = saml_user[:-len(strip_suffix)]

    log.debug('Looking for user with {!r} == {!r}'.format(user_main_attribute, saml_user))
    try:
        return request.userdb.get_user(saml_user)
    except request.userdb.exceptions.UserDoesNotExist:
        log.error('No user with {!r} = {!r} found'.format(user_main_attribute, saml_user))
    except request.userdb.exceptions.MultipleUsersReturned:
        log.error("There are more than one user with {!r} = {!r}".format(user_main_attribute, saml_user))
    return None


def login(request, session_info, user):
    """
    Update session with information about a user that has just logged in.

    :param request: Request object
    :param session_info: Session info received by pysaml2 client
    :param user: Information about user as returned by authenticate()
    :return:
    """
    main_attribute = request.registry.settings.get('saml2.user_main_attribute')
    log.info("User {!r} logging in ({!r}: {!r})".format(user['_id'], main_attribute, user[main_attribute]))
    request.session[main_attribute] = user[main_attribute]
    request.session['user'] = user
    request.session['eduPersonAssurance'] = get_loa(
        request.registry.settings.get('available_loa'),
        session_info
    )
    remember_headers = remember(request, user[main_attribute])
    return remember_headers


def logout(request):
    """
    Destroy session information when a user logs out.

    :param request:
    :return:
    """
    if 'user' in request.session:
        user = request.session['user']
        log.info("User {!r} logging out".format(user['_id']))

    if request.session is not None:
        request.session.delete()
    headers = forget(request)
    return headers
