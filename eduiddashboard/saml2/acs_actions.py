'''
Registry for actions to be performed after an IdP sends a POST
request in response to a SAML request initiated by the dashboard.

The actions are performed in the assertion consumer service view,
and are called with three positional parameters:

 * the HTTP request
 * the session_info given in the SAML response (a dict)
 * the user identified by the IdP
'''

import logging
logger = logging.getLogger(__name__)


_actions = {}


def register_action(action_key, action):
    '''
    Register a new action.
    This is used at the module level, and executed during initialization,
    when modules are imported/loaded.

    :param action_key: the key for the given action
    :type action_key: str
    :param action: the action to be performed
    :type action: function
    '''
    logger.info('Registering acs action ' + action_key)
    _actions[action_key] = action


def schedule_action(session, action_key):
    '''
    Schedule an action to be executed after an IdP responds to a SAML request.
    This is called just before the SAML request is sent.

    :param session: the session
    :type session: Session
    :param action_key: the key for the given action
    :type action_key: str
    '''
    logger.debug('Scheduling acs action ' + action_key)
    session['post-authn-action'] = action_key


def get_action(session):
    '''
    retrieve an action from the registry based on the key
    stored in the session.

    :param sesison: the session
    :type session: Session
    :return: the action
    :rtype: function
    '''
    try:
        action_key = session['post-authn-action']
    except KeyError:
        action_key = 'login-action'
    else:
        del session['post-authn-action']
    logger.debug('Consuming acs action ' + action_key)
    return _actions[action_key]
