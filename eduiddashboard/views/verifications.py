# Verifications links

from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from eduiddashboard.verifications import verificate_code


def verifications(context, request):
    model_name = request.matchdict['model']
    code = request.matchdict['code']

    obj_id = verificate_code(request, model_name, code)

    if obj_id is not None:
        return HTTPFound(location=request.route_url('home'))
    else:
        return HTTPNotFound()
