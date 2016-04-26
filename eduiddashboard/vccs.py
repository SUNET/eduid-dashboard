from bson import ObjectId
from datetime import datetime
from eduid_userdb.dashboard import DashboardLegacyUser, DashboardUser
from eduid_userdb import Password

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

    Returns False or a Password instance with data about the credential that validated.

    :param vccs_url: URL to VCCS authentication backend
    :param password: plaintext password
    :param user: User object
    :param vccs: optional vccs client instance

    :type vccs_url: string
    :type password: string
    :type user: DashboardUser or DashboardLegacyUser or User
    :type vccs: None or VCCSClient
    :rtype: False or Password
    """
    # upgrade DashboardLegacyUser to DashboardUser
    if isinstance(user, DashboardLegacyUser):
        user = DashboardUser(data=user._mongo_doc)

    for cred in user.passwords.to_list():
        if vccs is None:
            vccs = get_vccs_client(vccs_url)
        factor = vccs_client.VCCSPasswordFactor(
            password,
            credential_id=str(cred.id),
            salt=cred.salt,
            )
        try:
            if vccs.authenticate(str(user.user_id), [factor]):
                return cred
        except Exception as exc:
            log.warning("VCCS authentication threw exception: {!s}".format(exc))
            pass
    return False


def add_credentials(vccs_url, old_password, new_password, user):
    """
    Add a new password to a user. Revokes the old one, if one is given.

    Returns True on success.

    :param vccs_url: URL to VCCS authentication backend
    :param old_password: plaintext current password
    :param new_password: plaintext new password
    :param user: user object

    :type vccs_url: string
    :type old_password: string
    :type user: OldUser
    :rtype: bool
    """
    password_id = ObjectId()
    vccs = get_vccs_client(vccs_url)
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))

    if isinstance(user, DashboardLegacyUser):
        user = DashboardUser(data=user._mongo_doc)

    old_factor = None
    checked_password = None
    # remember if an old password was supplied or not, without keeping it in
    # memory longer than we have to
    old_password_supplied = bool(old_password)
    if user.passwords.count > 0 and old_password:
        # Find the old credential to revoke
        checked_password = check_password(vccs_url, old_password, user, vccs=vccs)
        del old_password  # don't need it anymore, try to forget it
        if not checked_password:
            return False
        old_factor = vccs_client.VCCSRevokeFactor(
            str(checked_password.id),
            'changing password',
            reference='dashboard',
        )

    if not vccs.add_credentials(str(user.user_id), [new_factor]):
        log.warning("Failed adding password credential {!r} for user {!r}".format(
            new_factor.credential_id, user))
        return False  # something failed
    log.debug("Added password credential {!s} for user {!s}".format(
        new_factor.credential_id, user))

    if old_factor:
        vccs.revoke_credentials(str(user.user_id), [old_factor])
        user.passwords.remove(checked_password.id)
        log.debug("Revoked old credential {!s} (user {!s})".format(
            old_factor.credential_id, user))

    if not old_password_supplied:
        # TODO: Revoke all current credentials on password reset for now
        revoked = []
        for password in user.passwords.to_list():
            revoked.append(vccs_client.VCCSRevokeFactor(str(password.id), 'reset password', reference='dashboard'))
            log.debug("Revoking old credential (password reset) {!s} (user {!r})".format(
                password.id, user))
            user.passwords.remove(password.id)
        if revoked:
            try:
                vccs.revoke_credentials(str(user.user_id), revoked)
            except vccs_client.VCCSClientHTTPError:
                # Password already revoked
                # TODO: vccs backend should be changed to return something more informative than
                # TODO: VCCSClientHTTPError when the credential is already revoked or just return success.
                log.warning("VCCS failed to revoke all passwords for user {!s}".format(user))
                pass

    new_password = Password(credential_id = password_id,
                            salt = new_factor.salt,
                            application = 'dashboard',
                            )
    user.passwords.add(new_password)

    return True


def provision_credentials(vccs_url, new_password, user):
    """
    This function should be used by tests only
    Provision new password to a user.

    Returns True on success.

    :param vccs_url: URL to VCCS authentication backend
    :param old_password: plaintext current password
    :param new_password: plaintext new password
    :param user: user object

    :type vccs_url: string
    :type old_password: string
    :type user: User
    :rtype: bool
    """
    password_id = ObjectId()
    vccs = get_vccs_client(vccs_url)
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))

    if not vccs.add_credentials(str(user.get_id()), [new_factor]):
        return False  # something failed

    passwords = user.get_passwords()
    passwords.append({
        'id': password_id,
        'salt': new_factor.salt,
    })
    user.set_passwords(passwords)

    return True


def revoke_all_credentials(vccs_url, user):
    vccs = get_vccs_client(vccs_url)
    passwords = user.passwords.to_list_of_dicts()
    to_revoke = []
    for passwd_dict in passwords:
        credential_id = str(passwd_dict['id'])
        factor = vccs_client.VCCSRevokeFactor(
            credential_id,
            'subscriber requested termination',
            reference='dashboard'
        )
        log.debug("Revoked old credential (account termination)"
                  " {!s} (user {!r})".format(
                      credential_id, user))
        to_revoke.append(factor)
    userid = str(user.user_id)
    vccs.revoke_credentials(userid, to_revoke)
