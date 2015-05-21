# Verifications links

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import get_localizer

from eduid_am.exceptions import UserOutOfSync
from eduiddashboard.views import sync_user
from eduiddashboard.verifications import verify_code, get_verification_code
from eduiddashboard.i18n import TranslationString as _

from eduiddashboard import log

@view_config(route_name='verifications', permission='edit')
def verifications(context, request):
    model_name = request.matchdict['model']
    code = request.matchdict['code']

    verification = get_verification_code(request, model_name, code=code)
    if verification and verification['expired']:
        log.debug("Verification code is expired: {!r}".format(verification))
        raise HTTPNotFound()  # the code is expired

    if code not in request.session.get('verifications', []):
        log.debug("Code {!r} not found in active sessions verifications: {!r}".format(
            code, request.session.get('verifications', [])))
        raise HTTPNotFound(_("Can't locate the code in the active session"))
    try:
        obj_id = verify_code(request, model_name, code)
    except UserOutOfSync:
        if 'edit-user' in request.session:
            user = request.session['edit-user']
        else:
            user = request.session['user']
        sync_user(request, context, user)
        msg = _('The user was out of sync. Please try again.')
        msg = get_localizer(request).translate(msg)
        request.session.flash(msg),
        raise HTTPFound(request.context.route_url('profile-editor'))

    if obj_id is not None:
        request.stats.count('dashboard/verification_{!s}_ok'.format(model_name), 1)
        return HTTPFound(location=request.route_url('home'))
    else:
        log.debug("Incorrect verification code {!r} for model {!r}".format(code, model_name))
        request.stats.count('dashboard/verification_{!s}_fail'.format(model_name), 1)
        raise HTTPNotFound()
