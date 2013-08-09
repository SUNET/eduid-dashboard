from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config

from eduiddashboard.models import Person
from eduiddashboard.utils import verify_auth_token


@view_config(route_name='home', renderer='templates/home.jinja2',
             request_method='GET', permission='edit')
def home(context, request):
    """
        HOME doesn't have forms. All forms are handle by ajax urls.
    """

    user = request.session.get('user', None)

    person_schema = Person()

    person = person_schema.serialize(user)
    context = {
        'person': person_schema.serialize(user),
    }

    # TODO
    if isinstance(user['email'], unicode):
        context['primary_email'] = user['email']
        context['emails'] = [
            {'email': user['email'], 'verified': user['verified']},
        ]
    else:
        context['primary_email'] = user.get('primary_email', '')
        context['emails'] = user['email']

    total_fields = len(person_schema.children)
    filled_fields = len(person.keys())
    for (key, value) in person.items():
        if not value:
            filled_fields -= 1

    context['profile_filled'] = (filled_fields / total_fields) * 100

    return context


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
        request.session['email'] = email
        request.session['user'] = user
        request.session['loa'] = 5
        remember_headers = remember(request, email)
        return HTTPFound(location=next_url, headers=remember_headers)
    else:
        # Show and error, the user can't be logged
        return HTTPBadRequest()
