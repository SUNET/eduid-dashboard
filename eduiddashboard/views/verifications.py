# Verifications links

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from eduiddashboard.verifications import verificate_code, get_verification_code
from eduiddashboard.i18n import TranslationString as _


@view_config(route_name='verifications', permission='edit')
def verifications(context, request):
    model_name = request.matchdict['model']
    code = request.matchdict['code']

    verification = get_verification_code(request, model_name, code=code)
    if verification and verification['expired']:
        raise HTTPNotFound()  # the code is expired

    if code not in request.session.get('verifications', []):
        raise HTTPNotFound(_("Can't locate the code in the active session"))

    obj_id = verificate_code(request, model_name, code)

    if obj_id is not None:
        return HTTPFound(location=request.route_url('home'))
    else:
        raise HTTPNotFound()
