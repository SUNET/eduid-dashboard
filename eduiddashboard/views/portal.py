import deform
import re

from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config
from pyramid.settings import asbool

from deform_bootstrap import Form

from eduiddashboard.utils import (verify_auth_token,
                                  calculate_filled_profile,
                                  get_pending_actions,
                                  get_max_available_loa,
                                  get_available_tabs)
from eduiddashboard.i18n import TranslationString as _

from eduiddashboard.views.nins import nins_open_wizard

from eduiddashboard.models import UserSearcher

import logging
logger = logging.getLogger(__name__)


@view_config(route_name='profile-editor', renderer='templates/profile.jinja2',
             request_method='GET', permission='edit')
def profile_editor(context, request):
    """
        Profile editor doesn't have forms. All forms are handle by ajax urls.
    """

    view_context = {}

    tabs = get_available_tabs(context, request)

    profile_filled = calculate_filled_profile(context.user, tabs)

    pending_actions = get_pending_actions(context.user, tabs)

    max_loa = get_max_available_loa(context.get_groups())
    max_loa = context.loa_to_int(loa=max_loa)

    (open_wizard, datakey) = nins_open_wizard(context, request)

    view_context = {
        'tabs': tabs,
        'userid': context.user.get(context.main_attribute),
        'user': context.user.get_doc(),
        'profile_filled': profile_filled,
        'pending_actions': pending_actions,
        'workmode': context.workmode,
        'max_loa': max_loa,
        'polling_timeout_for_admin': request.registry.settings.get(
            'polling_timeout_for_admin', 2000),
        'open_wizard': open_wizard,
        'datakey': datakey,
    }

    return view_context


SEARCHER_FIELDS = [
    'mailAliases.email',
    'mobile.mobile',
    'norEduPersonNIN',
    'givenName',
    'sn',
    'displayName'
]

SEARCH_RESULT_LIMIT = 100


@view_config(route_name='home', renderer='templates/home.jinja2',
             request_method='GET', permission='edit')
def home(context, request):
    """
    If workmode is not personal mode, then show an admin or helpdesk interface

    """

    if context.workmode == 'personal':
        raise HTTPFound(context.route_url('profile-editor'))

    searcher_schema = UserSearcher()
    buttons = (deform.Button(name='search', title=_('Search')),)
    searcher_form = Form(searcher_schema, buttons=buttons,
                         method='get', formid='user-searcher')

    users = None
    showresults = False

    if 'query' in request.GET:
        controls = request.GET.items()
        try:
            searcher_data = searcher_form.validate(controls)
        except deform.ValidationFailure, form:
            return {
                'form': form,
                'users': [],
                'showresults': False,
            }
        query_text = re.escape(searcher_data['query'])
        filter_dict = {'$or': []}
        field_filter = {'$regex': '.*%s.*' % query_text, '$options': 'i'}
        for field in SEARCHER_FIELDS:
            filter_dict['$or'].append({field: field_filter})

        users = request.userdb.get_users(filter_dict)

        showresults = True

    if users and users.count() > SEARCH_RESULT_LIMIT:
        request.session.flash(_('error|More than %d users returned. Please refine your search.' % SEARCH_RESULT_LIMIT))
        users.limit(SEARCH_RESULT_LIMIT)

    # if users and users.count() == 1:
    #    raise HTTPFound(request.route_url('profile-editor',
    #                    userid=users[0][context.main_attribute]))

    return {
        'form': searcher_form,
        'users': users,
        'showresults': showresults,
    }


@view_config(route_name='session-reload',
             request_method='GET', permission='edit')
def session_reload(context, request):
    main_attribute = request.registry.settings.get('saml2.user_main_attribute')
    userid = request.session.get('user').get(main_attribute)
    user = request.userdb.get_user(userid)
    request.session['user'] = user
    raise HTTPFound(request.route_path('home'))


@view_config(route_name='help')
def help(context, request):
    # We don't want to mess up the gettext .po file
    # with a lot of strings which don't belong to the
    # application interface.
    #
    # We consider the HELP as application content
    # so we simple use a different template for each
    # language. When a new locale is added to the
    # application it needs to translate the .po files
    # as well as this template

    locale_name = get_locale_name(request)
    template = 'eduiddashboard:templates/help-%s.jinja2' % locale_name

    return render_to_response(template, {'user':context.user.get_doc()}, request=request)


@view_config(route_name='token-login', request_method='POST')
def token_login(context, request):
    email = request.POST.get('email')
    token = request.POST.get('token')
    nonce = request.POST.get('nonce')
    timestamp = request.POST.get('ts')
    shared_key = request.registry.settings.get('auth_shared_secret')

    next_url = request.POST.get('next_url', '/')

    if verify_auth_token(shared_key, email, token, nonce, timestamp):
        # Do the auth
        user = request.userdb.get_user(email)
        request.session['mail'] = email
        request.session['user'] = user
        request.session['loa'] = 1
        remember_headers = remember(request, email)
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        logger.info("Token authentication failed (email: {!r})".format(email))
        # Show and error, the user can't be logged
        return HTTPBadRequest()


@view_config(route_name='set_language', request_method='GET')
def set_language(context, request):
    settings = request.registry.settings
    lang = request.GET.get('lang', 'en')
    if lang not in settings['available_languages']:
        return HTTPNotFound()

    url = request.environ.get('HTTP_REFERER', None)
    if url is None:
        url = request.route_path('home')
    response = HTTPFound(location=url)
    cookie_domain = settings.get('lang_cookie_domain', None)
    cookie_name = settings.get('lang_cookie_name')

    extra_options = {}
    if cookie_domain is not None:
        extra_options['domain'] = cookie_domain

    extra_options['httponly'] = asbool(settings.get('session.httponly'))
    extra_options['secure'] = asbool(settings.get('session.secure'))

    response.set_cookie(cookie_name, value=lang, **extra_options)

    return response


@view_config(route_name='error500test')
def error500view(context, request):
    raise Exception()


@view_config(route_name='error500', renderer='templates/error500.jinja2')
def exception_view(context, request):
    logger.error("The error was: %s" % context, exc_info=(context))
    request.response.status = 500
    #message = getattr(context, 'message', '')
    # `message' might include things like database connection details (with authentication
    # parameters), so it should NOT be displayed to the user.
    return {'msg': 'Code exception'}


@view_config(route_name='error404', renderer='templates/error404.jinja2')
def not_found_view(context, request):
    request.response.status = 404
    return {}
