import deform
import re

from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest, HTTPNotFound
from pyramid.httpexceptions import HTTPUnauthorized
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
from eduiddashboard.saml2.views import logout_view
from eduiddashboard.views.nins import nins_open_wizard
from eduiddashboard.views.mobiles import has_confirmed_mobile
from eduiddashboard.models import UserSearcher
from eduiddashboard.emails import send_termination_mail
from eduiddashboard.vccs import revoke_all_credentials
from eduiddashboard.saml2.views import get_authn_request
from eduiddashboard.saml2.utils import get_location
from eduiddashboard.saml2.acs_actions import acs_action, schedule_action

import logging
logger = logging.getLogger(__name__)


@view_config(route_name='profile-editor', renderer='templates/profile.jinja2',
             request_method='GET', permission='edit')
def profile_editor(context, request):
    """
        Profile editor doesn't have forms. All forms are handle by ajax urls.
    """

    context.user.retrieve_modified_ts(request.db.profiles)

    view_context = {}

    tabs = get_available_tabs(context, request)

    profile_filled = calculate_filled_profile(tabs)

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
        'has_mobile': has_confirmed_mobile(context.user),
        'nins_wizard_chooser_url': request.route_url('nins-wizard-chooser'),
        'nins_verification_chooser_url': request.route_url('nins-verification-chooser'),
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
    support_email = request.registry.settings.get('mail.support_email',
                                                  'support@eduid.se')
    template_context = {
        'user':context.user.get_doc(),
        'support_email': support_email
    }

    request.stats.count('dashboard/help_page_shown', 1)
    return render_to_response(template, template_context, request=request)


@view_config(route_name='token-login', request_method='POST')
def token_login(context, request):
    eppn = request.POST.get('eppn')
    token = request.POST.get('token')
    nonce = request.POST.get('nonce')
    timestamp = request.POST.get('ts')
    shared_key = request.registry.settings.get('auth_shared_secret')

    next_url = request.POST.get('next_url', '/')

    if verify_auth_token(shared_key, eppn, token, nonce, timestamp):
        # Do the auth
        user = request.userdb.get_user(eppn)
        request.session['mail'] = user.get('email'),
        request.session['user'] = user
        request.session['loa'] = 1
        remember_headers = remember(request, user.get('email'))
        request.stats.count('dashboard/token_login_success', 1)
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        logger.info("Token authentication failed (eppn: {!r})".format(eppn))
        request.stats.count('dashboard/token_login_fail', 1)
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
    request.stats.count('dashboard/set_language_cookie', 1)

    return response


@view_config(route_name='account-terminated',
             renderer='templates/account-terminated.jinja2',)
def account_terminated(context, request):
    '''
    landing page after account termination
    '''
    return {}


@acs_action('account-termination-action')
def account_termination_action(request, session_info, user):
    '''
    The account termination action,
    removes all credentials for the terminated account
    from the VCCS service,
    flags the account as terminated,
    sends an email to the address in the terminated account,
    and logs out the session.
    '''
    settings = request.registry.settings
    logged_user = request.session['user']

    if logged_user.get_id() != user.get_id():
        raise HTTPUnauthorized("Wrong user")

    # revoke all user credentials
    revoke_all_credentials(settings.get('vccs_url'), user)
    user.set_passwords([])

    # flag account as terminated
    user.set_terminated()
    user.save(request, check_sync=False)

    # email the user
    send_termination_mail(request, user)

    # logout
    next_page = request.POST.get('RelayState', '/')
    request.session['next_page'] = next_page
    return logout_view(request)


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
    csrf = request.POST.get('csrf')
    if csrf != request.session.get_csrf_token():
        return HTTPBadRequest()

    selected_idp = request.session.get('selected_idp')
    relay_state = context.route_url('account-terminated')
    loa = context.get_loa()
    info = get_authn_request(request, relay_state, selected_idp,
                             required_loa=loa, force_authn=True)
    schedule_action(request.session, 'account-termination-action')

    return HTTPFound(location=get_location(info))


@view_config(route_name='nins-wizard-chooser',
             renderer='templates/nins-wizard-chooser.jinja2',
             request_method='GET', permission='edit')
def nins_wizard_chooser(context, request):
    return {
            'has_mobile': has_confirmed_mobile(context.user),
            }


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
