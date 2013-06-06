from pyramid.i18n import get_locale_name
from pyramid.renderers import render_to_response
from pyramid.view import view_config


@view_config(route_name='home', renderer='templates/home.jinja2')
def home(context, request):
    return {}


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
