# Verifications links

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import get_localizer

from eduid_userdb.exceptions import UserOutOfSync
from eduiddashboard.session import get_session_user
from eduiddashboard.utils import retrieve_modified_ts
from eduiddashboard.verifications import (get_verification_code,
                                          verify_code,
                                          set_phone_verified,
                                          set_email_verified)
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
        msg = _('Your user profile is out of sync. Please '
                'reload the page and try again.')
        msg = get_localizer(request).translate(msg)
        request.session.flash(msg),
        raise HTTPFound(request.context.route_url('profile-editor'))

    if obj_id is not None:
        request.stats.count('verification_{!s}_ok'.format(model_name))
        return HTTPFound(location=request.route_url('home'))
    else:
        db, data_id, proofing_states = None, None, []
        user = get_session_user(request, legacy_user=False)
        retrieve_modified_ts(user, request.dashboard_userdb)
        if model_name == 'mailAliases':
            db = request.new_email_proofing_state_db
            proofing_states = db._get_documents_by_attr('eduPersonPrincipalName', user.eppn,
                    raise_on_missing=False)
        elif model_name == 'phone':
            db = request.new_phone_proofing_state_db
            proofing_states = db._get_documents_by_attr('eduPersonPrincipalName', user.eppn,
                    raise_on_missing=False)
        else:
            raise NotImplementedError('Unknown validation model_name: {!r}'.format(model_name))
        for ps in proofing_states:
            proofing_state = db.ProofingStateClass(ps)
            if code_sent == proofing_state.verification.verification_code:
                if model_name == 'phone':
                    data_id = proofing_state.verification.number
                    msg = set_phone_verified(request, user, data_id)
                elif model_name == 'mailAliases':
                    data_id = proofing_state.verification.email
                    msg = set_email_verified(request, user, data_id)

                try:
                    request.context.save_dashboard_user(user)
                    log.info("Verified {!s} saved for user {!r}.".format(model_name, user))
                except UserOutOfSync:
                    log.info("Verified {!s} NOT saved for user {!r}. User out of sync.".format(model_name, user))
                    raise
                db.remove_state(proofing_state)
                log.debug('Removed proofing state: {!r} '.format(proofing_state))
                request.stats.count('verification_{!s}_ok'.format(model_name))
                return HTTPFound(location=request.route_url('home'))

        log.debug("Incorrect verification code {!r} for model {!r}".format(code, model_name))
        request.stats.count('verification_{!s}_fail'.format(model_name))
        raise HTTPNotFound()
