"""
Level of assurance related code.
"""

AVAILABLE_LOA_LEVEL = [
    'http://www.swamid.se/policy/assurance/al1',
    'http://www.swamid.se/policy/assurance/al2',
    'http://www.swamid.se/policy/assurance/al3',
]


MAX_LOA_ROL = {
    'user': AVAILABLE_LOA_LEVEL[0],
    'helpdesk': AVAILABLE_LOA_LEVEL[1],
    'admin': AVAILABLE_LOA_LEVEL[2],
}


def get_max_available_loa(groups):
    if not groups:
        return MAX_LOA_ROL['user']
    loas = [v for (k, v) in MAX_LOA_ROL.iteritems() if k in groups]
    if len(loas) > 0:
        return max(loas)
    else:
        return MAX_LOA_ROL['user']


