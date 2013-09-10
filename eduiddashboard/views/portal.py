import deform

from pyramid.i18n import get_locale_name
from pyramid.i18n import TranslationString as _
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config

from deform_bootstrap import Form

from eduiddashboard.utils import verify_auth_token, filter_tab
from eduiddashboard.models import UserSearcher

from eduiddashboard.views import emails, personal, get_dummy_status

AVAILABLE_TABS = [
    personal.get_tab(),
    emails.get_tab(),
    {
        'label': _('Authorization'),
        'status': get_dummy_status,
        'id': 'authorization',
    }, {
        'label': _('Passwords'),
        'status': get_dummy_status,
        'id': 'passwords',
    }, {
        'label': _('Phones'),
        'status': get_dummy_status,
        'id': 'phones',
    }, {
        'label': _('Postal Address'),
        'status': get_dummy_status,
        'id': 'postaladdress',
    },
]


@view_config(route_name='profile-editor', renderer='templates/profile.jinja2',
             request_method='GET', permission='edit')
def profile_editor(context, request):
    """
        Profile editor doesn't have forms. All forms are handle by ajax urls.
    """

    view_context = {}

    # TODO we need to count fields from all schemas
    # user = request.session.get('user', None)
    # person = person_schema.serialize(user)
    #
    # total_fields = len(person_schema.children)
    # filled_fields = len(person.keys())
    # for (key, value) in person.items():
    #     if not value:
    #         filled_fields -= 1
    # view_context['profile_filled'] = (filled_fields / total_fields) * 100

    view_context['profile_filled'] = 78

    view_context['userid'] = context.user.get(context.main_attribute)
    view_context['user'] = context.user

    if context.workmode == 'personal':
        view_context['tabs'] = filter_tab(AVAILABLE_TABS, ['authorization'])

    elif context.workmode == 'helpdesk':
        view_context['tabs'] = filter_tab(AVAILABLE_TABS, ['passwords',
                                                           'authorization'])
    else:
        view_context['tabs'] = AVAILABLE_TABS

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
    context.update_user()
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
        request.session['loa'] = 5
        remember_headers = remember(request, email)
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        # Show and error, the user can't be logged
        return HTTPBadRequest()