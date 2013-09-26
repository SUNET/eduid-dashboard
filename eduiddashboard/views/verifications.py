# Verifications links

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from eduiddashboard.verifications import verificate_code


@view_config(route_name='verifications', permission='edit')
def verifications(context, request):
    model_name = request.matchdict['model']
    code = request.matchdict['code']

    obj_id = verificate_code(request, model_name, code)

    if obj_id is not None:
        return HTTPFound(location=request.route_url('home'))
    else:
        return HTTPNotFound()
