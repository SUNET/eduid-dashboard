from saml2.config import SPConfig
import imp

import logging
logger = logging.getLogger(__name__)



def get_saml2_config(module_path):

    module = imp.load_source('saml2_settings', module_path)

    conf = SPConfig()
    conf.load(module.SAML_CONFIG)
    return conf


def get_saml2_config_from_request(request):
    module_path = request.registry.settings.get('saml2.settings_module')
    return get_saml2_config(module_path)


def get_location(http_info):
    """Extract the redirect URL from a pysaml2 http_info object"""
    assert 'headers' in http_info
    headers = http_info['headers']

    assert len(headers) == 1
    header_name, header_value = headers[0]
    assert header_name == 'Location'
    return header_value

def get_SAML_attribute(session_info, attr_name):
    # Get attributes we received from the SAML IdP. This is a dictionary like
    # {'mail': ['user@example.edu'],
    #  'eduPersonPrincipalName': ['gadaj-fifib@idp.example.edu']
    # }
    if not 'ava' in session_info:
        raise ValueError('SAML attributes (ava) not found in session_info')

    attributes = session_info['ava']

    logger.debug('SAML attributes received: %s' % attributes)

    attr_name = attr_name.lower()
    # Look for the canonicalized attribute in the SAML assertion attributes
    for saml_attr, local_fields in attributes.items():
        if saml_attr.lower() == attr_name:
            return attributes[saml_attr]
