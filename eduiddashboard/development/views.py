# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from pyramid.httpexceptions import HTTPFound
from pyramid.security import authenticated_userid, forget
from pyramid.view import view_config
from .auth import login

from eduiddashboard import log


@view_config(route_name='saml2-login')
def login_view(request):
    login_redirect_url = request.registry.settings.get(
        'saml2.login_redirect_url', '/')

    came_from = request.GET.get('next', login_redirect_url)
    if authenticated_userid(request):
        return HTTPFound(location=came_from)

    username = request.registry.settings.get('development_user')
    request, headers = login(request, username)

    return HTTPFound(location='/', headers=headers)


@view_config(route_name='saml2-logout')
def logout_view(request):
    headers = forget(request)
    return HTTPFound(location='/help/', headers = headers)