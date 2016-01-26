from pyramid.view import view_config

from eduiddashboard.utils import (calculate_filled_profile,
                                  get_available_tabs,
                                  get_pending_actions)
from eduiddashboard.loa import get_max_available_loa

import logging
logger = logging.getLogger(__name__)


@view_config(route_name='userstatus', permission='edit', renderer='json')
def userstatus(context, request):
    """
    Calculate the percentage of profile completeness that is displayed to the user with a bar.

    :param context:
    :param request:
    :return: Dict
    """
    tabs = get_available_tabs(context, request)
    profile_filled = calculate_filled_profile(tabs)
    return {
        'loa': request.session.get('loa', 1),
        'max_loa': get_max_available_loa(context.get_groups()),
        'profile_filled': '{!s}%'.format(profile_filled),
        'pending_actions': get_pending_actions(context.user, tabs),
    }
