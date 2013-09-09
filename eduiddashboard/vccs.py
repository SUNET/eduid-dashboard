from bson import ObjectId

import vccs_client


def check_password(vccs_url, password, user):
    """ return False or the password dict related
        to the password literal passed by param """
    if 'passwords' in user:
        for password_dict in user['passwords']:
            password_id = password_dict['id']
            vccs = vccs_client.VCCSClient(
                base_url=vccs_url,
            )
            factor = vccs_client.VCCSPasswordFactor(
                password,
                credential_id=str(password_id),
                salt=password_dict['salt'],
            )
            try:
                if vccs.authenticate(user['mail'], [factor]):
                    return password_dict
            except Exception, exc:
                pass
    return False


def add_credentials(vccs_url, old_password, new_password, user):
    """ add new credentials to the user in session """
    password_id = ObjectId()
    vccs = vccs_client.VCCSClient(
        base_url=vccs_url,
    )
    new_factor = vccs_client.VCCSPasswordFactor(new_password,
                                                credential_id=str(password_id))
    if not vccs.add_credentials(user['mail'], [new_factor]):
        return False  # something failed

    if 'passwords' not in user:
        passwords = []
    else:
        passwords = user['passwords']

    if passwords:
        # revoking old credentials
        old_password = check_password(vccs_url, old_password, user)
        if old_password:
            old_factor = vccs_client.VCCSRevokeFactor(
                str(old_password['id']),
                'changing password',
                reference='dashboard',
            )
            vccs.revoke_credentials(user['mail'], [old_factor])
            passwords.remove(old_password)

    passwords.append({
        'id': password_id,
        'salt': new_factor.salt,
    })
    user['passwords'] = passwords

    return True
