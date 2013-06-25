from pyramid.i18n import get_locale_name
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from pyramid.renderers import render_to_response
from pyramid.security import remember
from pyramid.view import view_config

from deform import Form, ValidationFailure

from eduid_am.tasks import update_attributes

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.models import Person
from eduiddashboard.utils import verify_auth_token, flash


@view_config(route_name='home', renderer='templates/home.jinja2',
             permission='edit')
def home(context, request):
    user = request.session.get('user', None)
    person_schema = Person()
    person_form = Form(person_schema, buttons=('submit',))
    if request.POST:
        controls = request.POST.items()
        try:
            user_modified = person_form.validate(controls)
        except ValidationFailure:
            flash(request, 'error',
                  _('Please fix the highlighted errors in the form'))
            person = person_schema.serialize(user)
        else:
            person = person_schema.serialize(user_modified)
            # update the session data
            request.session['user'].update(person)

            # Remove items from changes queue, if exists
            request.db.profiles.remove({
                '_id': user['_id'],
            })

            # Insert the new user object
            request.db.profiles.insert(user, safe=True)

            update_attributes.delay('eduid_dashboard', str(user['_id']))

            # Do the save staff
            flash(request, 'info',
                  _('Your changes was saved, please, wait before your changes'
                    'are distributed through all applications'))
            return HTTPFound(request.route_url('home'))

    person = person_schema.serialize(user)

    total_fields = len(person_schema.children)
    filled_fields = len(person.keys())
    for (key, value) in person.items():
        if not value:
            filled_fields -= 1

    return {
        'person': person,
        'person_form': person_form,
        'profile_filled': (filled_fields / total_fields) * 100,
    }


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
