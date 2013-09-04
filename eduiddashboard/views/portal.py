from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config

from eduiddashboard.utils import verify_auth_token


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

    return view_context


@view_config(route_name='home', renderer='templates/home.jinja2',
             request_method='GET', permission='edit')
def home(context, request):
    """
        HOME doesn't have forms. All forms are handle by ajax urls.
    """

    if context.workmode == 'personal':
        raise HTTPFound(context.route_url('profile-editor'))

    return {}


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
