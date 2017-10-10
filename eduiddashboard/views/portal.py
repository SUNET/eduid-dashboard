import deform
import re
from datetime import datetime
import urlparse
from urllib import urlencode

from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest, HTTPNotFound
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config
from pyramid.settings import asbool

from deform_bootstrap import Form

from eduid_common.api.utils import urlappend
from eduiddashboard.utils import (verify_auth_token,
                                  calculate_filled_profile,
                                  get_pending_actions,
                                  get_available_tabs,
                                  sanitize_get,
                                  sanitize_post_key)
from eduiddashboard.loa import get_max_available_loa
from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.views.mobiles import has_confirmed_mobile
from eduiddashboard.models import UserSearcher
from eduiddashboard.emails import send_termination_mail
from eduiddashboard.vccs import revoke_all_credentials
from eduiddashboard.session import store_session_user, get_logged_in_user, get_session_user

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

    profile_filled = calculate_filled_profile(tabs)

    pending_actions = get_pending_actions(context.user, tabs)

    max_loa = get_max_available_loa(context.get_groups())
    max_loa = context.loa_to_int(loa=max_loa)

    enable_mm = request.registry.settings.get('enable_mm_verification')

    if context.main_attribute == 'mail' and context.user.mail_addresses.primary:
        userid = context.user.mail_addresses.primary.email
    else:
        userid =  context.user.eppn

    view_context = {
        'tabs': tabs,
        'userid': userid,
        'user': context.user,
        'profile_filled': profile_filled,
        'pending_actions': pending_actions,
        'workmode': context.workmode,
        'max_loa': max_loa,
        'polling_timeout_for_admin': request.registry.settings.get(
            'polling_timeout_for_admin', 2000),
        'has_mobile': has_confirmed_mobile(context.user),
        'enable_mm_verification': enable_mm,
    }
    if enable_mm:
        view_context.update({
            'nins_verification_chooser_url': context.safe_route_url('nins-verification-chooser'),
        })

    return view_context


SEARCHER_FIELDS = [
    'mailAliases.email',
    'phone.number',
    'norEduPersonNIN',
    'givenName',
    'surname',
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

    if sanitize_get(request, 'query') is not None:
        controls = request.GET.items()
        try:
            searcher_data = searcher_form.validate(controls)
        except deform.ValidationFailure as form:
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


# Seems unused -- ft@ 2016-01-14
#@view_config(route_name='session-reload',
#             request_method='GET', permission='edit')
#def session_reload(context, request):
#    eppn = request.session.get('user').get('eduPersonPrincipalName')
#    user = request.userdb.get_user_by_eppn(eppn)
#    request.session['user'] = user
#    raise HTTPFound(request.route_path('home'))


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
    support_email = request.registry.settings.get('mail.support_email',
                                                  'support@eduid.se')
    template_context = {
        'user':context.user.to_dict(),
        'support_email': support_email
    }

    request.stats.count('help_page_shown')
    return render_to_response(template, template_context, request=request)


@view_config(route_name='token-login', request_method='POST')
def token_login(context, request):
    eppn = sanitize_post_key(request, 'eppn')
    token = sanitize_post_key(request, 'token')
    nonce = sanitize_post_key(request, 'nonce')
    timestamp = sanitize_post_key(request, 'ts')
    shared_key = request.registry.settings.get('auth_shared_secret')

    next_url = sanitize_post_key(request, 'next_url', '/')

    if verify_auth_token(shared_key, eppn, token, nonce, timestamp):
        # Do the auth
        user = request.userdb_new.get_user_by_eppn(eppn)
        store_session_user(request, user)
        if user.mail_addresses.primary:
            userid = user.mail_addresses.primary.email
        else:
            userid = eppn
        remember_headers = remember(request, userid)
        request.stats.count('token_login_success')
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        logger.info("Token authentication failed (eppn: {!r})".format(eppn))
        request.stats.count('token_login_fail')
        # Show and error, the user can't be logged
        return HTTPBadRequest()


@view_config(route_name='logout')
def logout(context, request):
    settings = request.registry.settings
    authn_url = settings.get('token_service_url')
    logout_url = urlappend(authn_url, 'logout')
    return HTTPFound(location=logout_url)


@view_config(route_name='set_language', request_method='GET')
def set_language(context, request):
    import re

    settings = request.registry.settings
    lang = sanitize_get(request, 'lang', 'en')
    if lang not in settings['available_languages']:
        return HTTPNotFound()

    url = request.environ.get('HTTP_REFERER', None)
    host = request.environ.get('HTTP_HOST', None)

    dashboard_hostname = settings.get('dashboard_hostname')
    dashboard_baseurl = settings.get('dashboard_baseurl')

    # To avoid malicious redirects, using header injection, we only
    # allow the client to be redirected to an URL that is within the
    # predefined scope of the application.
    allowed_url = re.compile('^(http|https)://' + dashboard_hostname + '[:]{0,1}\d{0,5}($|/)')
    allowed_host = re.compile('^' + dashboard_hostname + '[:]{0,1}\d{0,5}$')

    if url is None or not allowed_url.match(url):
        url = dashboard_baseurl
    elif host is None or not allowed_host.match(host):
        url = dashboard_baseurl

    response = HTTPFound(location=url)

    cookie_domain = settings.get('lang_cookie_domain', None)
    cookie_name = settings.get('lang_cookie_name')

    extra_options = {}
    if cookie_domain is not None:
        extra_options['domain'] = cookie_domain

    extra_options['httponly'] = asbool(settings.get('session.httponly'))
    extra_options['secure'] = asbool(settings.get('session.secure'))

    response.set_cookie(cookie_name, value=lang, **extra_options)
    request.stats.count('set_language_cookie')

    return response


@view_config(route_name='account-terminated',
             renderer='templates/account-terminated.jinja2',)
def account_terminated(context, request):
    """
    The account termination action,
    removes all credentials for the terminated account
    from the VCCS service,
    flags the account as terminated,
    sends an email to the address in the terminated account,
    and logs out the session.

    :type user: eduid_userdb.dashboard.DashboardLegacyUser
    """
    settings = request.registry.settings

    authn_ts = request.session.get('reauthn-for-termination', None)
    if authn_ts is None:
        raise HTTPBadRequest(_('No authentication info'))
    now = datetime.utcnow()
    delta = now - datetime.fromtimestamp(authn_ts)
    # XXX put the reauthn timeout in the settings
    if int(delta.total_seconds()) > 600:
        msg = _('Stale authentication info. Please try again.')
        request.session.flash('error|' + msg)
        raise HTTPFound(context.route_url('profile-editor'))

    user = get_session_user(request)
    logger.debug('Removing Authn ts for user {!r} before'
            ' changing the password'.format(user))
    del request.session['reauthn-for-termination']

    logged_user = get_logged_in_user(request, legacy_user = False)
    if logged_user.user_id != user.user_id:
        raise HTTPUnauthorized("Wrong user")

    logger.info("Terminating user {!s}".format(user))

    # revoke all user credentials
    revoke_all_credentials(settings.get('vccs_url'), user)
    for p in logged_user.passwords.to_list():
        logged_user.passwords.remove(p.credential_id)

    # flag account as terminated
    logged_user.terminated = True
    request.context.save_dashboard_user(logged_user)

    # email the user
    send_termination_mail(request, logged_user)

    return {}


@view_config(route_name='terminate-account', request_method='POST',
             permission='edit')
def terminate_account(context, request):
    '''
    Terminate account view.
    It receives a POST request, checks the csrf token,
    schedules the account termination action,
    and redirects to the IdP.
    '''
    settings = request.registry.settings

    # check csrf
    csrf = sanitize_post_key(request, 'csrf')
    if csrf != request.session.get_csrf_token():
        return HTTPBadRequest()

    ts_url = request.registry.settings.get('token_service_url')
    terminate_url = urlappend(ts_url, 'terminate')
    next_url = request.route_url('account-terminated')

    params = {'next': next_url}

    url_parts = list(urlparse.urlparse(terminate_url))
    query = urlparse.parse_qs(url_parts[4])
    query.update(params)

    url_parts[4] = urlencode(query)
    location = urlparse.urlunparse(url_parts)
    return HTTPFound(location=location)


@view_config(route_name='nins-verification-chooser',
             renderer='templates/nins-verification-chooser.jinja2',
             request_method='GET', permission='edit')
def nins_verification_chooser(context, request):
    return {
            'has_mobile': has_confirmed_mobile(context.user),
            }


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
