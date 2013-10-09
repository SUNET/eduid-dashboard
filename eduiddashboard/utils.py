from hashlib import sha256
from uuid import uuid4

from pyramid.i18n import TranslationString as _

from eduiddashboard.compat import text_type

from eduiddashboard import AVAILABLE_LOA_LEVEL

MAX_LOA_ROL = {
    'user': AVAILABLE_LOA_LEVEL[0],
    'helpdesk': AVAILABLE_LOA_LEVEL[1],
    'admin': AVAILABLE_LOA_LEVEL[2],
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


def get_available_tabs(context):
    from eduiddashboard.views import (emails, personal, postal_address,
                                      mobiles, nins, permissions,
                                      get_dummy_status)
    default_tabs = [
        personal.get_tab(),
        nins.get_tab(),
        emails.get_tab(),
        permissions.get_tab(),
        {
            'label': _('Passwords'),
            'status': get_dummy_status,
            'id': 'passwords',
        },
        mobiles.get_tab(),
        postal_address.get_tab(),
    ]
    if context.workmode == 'personal':
        tabs = filter_tabs(default_tabs, ['permissions'])
    elif context.workmode == 'helpdesk':
        tabs = filter_tabs(default_tabs, ['passwords', 'authorization'])
    else:
        tabs = default_tabs
    for tab in tabs:
        tab['status'] = tab['status'](context.user)
    return tabs


def calculate_filled_profile(user, tabs):
    tuples = []
    for tab in tabs:
        if tab['status'] is not None:
            status = tab['status']
            if status is not None:
                tuples.append(status.get('completed'))

    filled_profile = [sum(a) for a in zip(*tuples)]
    return int((float(filled_profile[0]) / float(filled_profile[1])) * 100)


def get_pending_actions(user, tabs):
    tuples = []
    for tab in tabs:
        if tab['status'] is not None:
            status = tab['status']
            if status and 'pending_actions' in status:
                tuples.append((
                    tab['id'],
                    status['pending_actions']
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


def get_unique_hash():
    return text_type(uuid4())


def get_short_hash(entropy=6):
    return uuid4().hex[:entropy]
