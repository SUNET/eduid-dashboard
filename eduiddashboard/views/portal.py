import deform

from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config

from deform_bootstrap import Form

from eduiddashboard.utils import (verify_auth_token,
                                  calculate_filled_profile,
                                  get_pending_actions,
                                  get_max_available_loa,
                                  get_available_tabs)

from eduiddashboard.models import UserSearcher


@view_config(route_name='profile-editor', renderer='templates/profile.jinja2',
             request_method='GET', permission='edit')
def profile_editor(context, request):
    """
        Profile editor doesn't have forms. All forms are handle by ajax urls.
    """

    view_context = {}

    tabs = get_available_tabs(context)

    profile_filled = calculate_filled_profile(context.user, tabs)

    pending_actions = get_pending_actions(context.user, tabs)

    max_loa = get_max_available_loa(context.get_groups())
    max_loa = context.loa_to_int(loa=max_loa)

    view_context = {
        'tabs': tabs,
        'userid': context.user.get(context.main_attribute),
        'user': context.user,
        'profile_filled': profile_filled,
        'pending_actions': pending_actions,
        'workmode': context.workmode,
        'max_loa': max_loa,
        'polling_timeout_for_admin': request.registry.settings.get('polling_timeout_for_admin', 2000),
    }

    return view_context


SEARCHER_KEYS_MAPPING = {
    'mail': 'mailAliases.email',
    'mobile': 'mobile.mobile',
    'norEduPersonNIN': 'norEduPersonNIN.norEduPersonNIN',
}


@view_config(route_name='home', renderer='templates/home.jinja2',
             request_method='GET', permission='edit')
def home(context, request):
    """
        If workmode is not personal mode, then show a user searcher
    """

    if context.workmode == 'personal':
        raise HTTPFound(context.route_url('profile-editor'))

    searcher_schema = UserSearcher()
    searcher_form = Form(searcher_schema, buttons=('search', ),
                         method='get', formid='user-searcher')

    users = []
    showresults = False

    if 'search' in request.GET:
        controls = request.GET.items()
        try:
            searcher_data = searcher_form.validate(controls)
        except deform.ValidationFailure, form:
            return {
                'form': form,
                'users': [],
                'showresults': False,
            }

        filter_key = SEARCHER_KEYS_MAPPING.get(searcher_data['attribute_type'])
        if searcher_data['attribute_type'] in SEARCHER_KEYS_MAPPING:
            filter_dict = {
                filter_key: searcher_data['text']
            }
        else:
            filter_dict = None

        if filter_dict:
            users = request.userdb.get_users(filter_dict)

        showresults = True

    if users and users.count() == 1:
        raise HTTPFound(request.route_url('profile-editor',
                        userid=users[0][context.main_attribute]))

    return {
        'form': searcher_form,
        'users': users,
        'showresults': showresults,
    }


@view_config(route_name='session-reload',
             request_method='GET', permission='edit')
def session_reload(context, request):
    main_attribute = request.registry.settings.get('saml2.user_main_attribute')
    userid = request.session.get('user', {}).get(main_attribute)
    user = request.userdb.get_user(userid)
    request.session['user'] = user
    raise HTTPFound(request.route_path('home'))


@view_config(route_name='help')
def help(request):
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

    return render_to_response(template, {}, request=request)


@view_config(route_name='token-login', request_method='POST')
def token_login(context, request):
    email = request.POST.get('email')
    token = request.POST.get('token')
    shared_key = request.registry.settings.get('auth_shared_secret')

    next_url = request.POST.get('next_url', '/')

    if verify_auth_token(shared_key, email, token):
        # Do the auth
        user = request.userdb.get_user(email)
        request.session['mail'] = email
        request.session['user'] = user
        request.session['loa'] = 1
        remember_headers = remember(request, email)
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        # Show and error, the user can't be logged
        return HTTPBadRequest()
