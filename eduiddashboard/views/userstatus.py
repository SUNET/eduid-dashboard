from pyramid.view import view_config

from eduiddashboard.utils import (calculate_filled_profile,
                                  get_available_tabs,
                                  get_max_available_loa,
                                  get_pending_actions)


@view_config(route_name='userstatus', permission='edit', renderer='json')
def userstatus(context, request):
    user = context.user
    tabs = get_available_tabs(context)
    profile_filled = calculate_filled_profile(context.user, tabs)
    return {
        'loa': request.session.get('loa', 1),
        'max_loa': get_max_available_loa(context.get_groups()),
        'profile_filled': '%s%%' % profile_filled,
        'pending_actions': get_pending_actions(user, tabs),
    }
