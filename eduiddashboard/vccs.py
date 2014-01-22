from bson import ObjectId
from datetime import datetime

import vccs_client

from eduiddashboard import log


def get_vccs_client(vccs_url):
    """
    Instantiate a VCCS client.

    :param vccs_url: VCCS authentication backend URL
    :type vccs_url: string
    :return: vccs client
    :rtype: VCCSClient
    """
    return vccs_client.VCCSClient(
        base_url=vccs_url,
    )


def check_password(vccs_url, password, user, vccs=None):
    """ Try to validate a user provided password.

    Returns False or a dict with data about the credential that validated.

    :param vccs_url: URL to VCCS authentication backend
    :param password: plaintext password
    :param user: user dict
    :param vccs: optional vccs client instance

    :type vccs_url: string
    :type password: string
    :type user: dict
    :type vccs: None or VCCSClient
    :rtype: bool or dict
    """
    if 'passwords' in user:
        for password_dict in user['passwords']:
            password_id = password_dict['id']
            if vccs is None:
                vccs = get_vccs_client(vccs_url)
            factor = vccs_client.VCCSPasswordFactor(
                password,
                credential_id=str(password_id),
                salt=password_dict['salt'],
            )
            # Old credentials were created using the username (user['mail']) of the user
            # instead of the user['_id']. Try both during a transition period.
            user_ids = [str(user['_id']), user['mail']]
            if password_dict.get('user_id_hint') is not None:
                user_ids.insert(0, password_dict.get('user_id_hint'))
            try:
                for user_id in user_ids:
                    if vccs.authenticate(user_id, [factor]):
                        password_dict['user_id_hint'] = user_id
                        return password_dict
            except Exception:
                pass
    return False


def add_credentials(vccs_url, old_password, new_password, user):
    """
    Add a new password to a user. Revokes the old one, if one is given.

    Returns True on success.

    :param vccs_url: URL to VCCS authentication backend
    :param old_password: plaintext current password
    :param new_password: plaintext new password
    :param user: user dict

    :type vccs_url: string
    :type old_password: string
    :type user: dict
    :rtype: bool
    """
    password_id = ObjectId()
    vccs = get_vccs_client(vccs_url)
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))

    passwords = user.get('passwords', [])
    old_factor = None
    if passwords and old_password:
        # Find the old credential to revoke
        old_password = check_password(vccs_url, old_password, user, vccs=vccs)
        if not old_password:
            return False
        old_factor = vccs_client.VCCSRevokeFactor(
            str(old_password['id']),
            'changing password',
            reference='dashboard',
        )

    if not vccs.add_credentials(str(user['_id']), [new_factor]):
        log.warning("Failed adding password credential {!r} for user {!r}".format(
            new_factor.credential_id, user['_id']))
        return False  # something failed
    log.debug("Added password credential {!s} for user {!s}".format(
        new_factor.credential_id, user['_id']))

    if old_factor:
        # Use the user_id_hint inserted by check_password() until we know all
        # credentials use str(user['_id']) as user_id.
        vccs.revoke_credentials(old_password['user_id_hint'], [old_factor])
        passwords.remove(old_password)
        log.debug("Revoked old credential {!s} (user {!s})".format(
            old_factor.credential_id, user['_id']))

    passwords.append({
        'id': password_id,
        'salt': new_factor.salt,
        'source': 'dashboard',
        'created_ts': datetime.now(),
    })
    user['passwords'] = passwords

    return True
