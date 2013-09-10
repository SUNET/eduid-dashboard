from hashlib import sha256

MAX_LOA_ROL = {
    'user': 3,
    'helpdesk': 2,
    'admin': 2,
}


def verify_auth_token(shared_key, public_word, token, generator=sha256):
    return token == generator("{0}{1}".format(shared_key,
                                              public_word)).hexdigest()


def flash(request, message_type, message):
    request.session.flash("{0}|{1}".format(message_type, message))


def get_icon_string(status):
    return "icon-{0}".format(status)


def filter_tabs(tabs, remove_tabs):
    return filter(lambda tab: tab['id'] not in remove_tabs, tabs)


def calculate_filled_profile(user, tabs):
    tuples = []
    for tab in tabs:
        if tab['status'] is not None:
            status = tab['status'](user)
            if status is not None:
                tuples.append(status.get('completed'))

    return [sum(a) for a in zip(*tuples)]


def get_pending_actions(user, tabs):
    tuples = []
    for tab in tabs:
        if tab['status'] is not None:
            status = tab['status'](user)
            if status:
                tuples.append((
                    tab.get('id'),
                    status.get('pending_actions')
                ))

    return tuples


def get_max_available_loa(groups):
    if not groups:
        return MAX_LOA_ROL['user']
    loas = [v for (k, v) in MAX_LOA_ROL.iteritems() if k in groups]
    if len(loas) > 0:
        return max(loas)
    else:
        return MAX_LOA_ROL['user']
