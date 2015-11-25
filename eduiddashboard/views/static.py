from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound


@view_config(name='favicon.ico')
def favicon_view(context, request):
    return HTTPFound(request.static_url('eduiddashboard:static/favicon.ico'))