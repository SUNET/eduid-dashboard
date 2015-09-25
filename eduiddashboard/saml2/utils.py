from saml2.config import SPConfig
import imp

from eduiddashboard import log

from cgi import escape
from urllib import unquote, quote

from pyramid.httpexceptions import HTTPBadRequest


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


def get_saml_attribute(session_info, attr_name):
    """
    Get value from a SAML attribute received from the SAML IdP.

    session_info is a pysaml2 response.session_info(). This is a dictionary like
        {'mail': ['user@example.edu'],
         'eduPersonPrincipalName': ['gadaj-fifib@idp.example.edu']
      }

    :param session_info: SAML attributes received by pysaml2 client.
    :param attr_name: The attribute to look up
    :returns: Attribute values

    :type session_info: dict()
    :type attr_name: string()
    :rtype: [string()]
    """
    if not 'ava' in session_info:
        raise ValueError('SAML attributes (ava) not found in session_info')

    attributes = session_info['ava']

    log.debug('SAML attributes received: %s' % attributes)

    attr_name = attr_name.lower()
    # Look for the canonicalized attribute in the SAML assertion attributes
    for saml_attr, local_fields in attributes.items():
        if saml_attr.lower() == attr_name:
            return attributes[saml_attr]

def sanitize_url(url):
    """
    Sanitize an URL

    If the URL is not quoted we only escape it. Otherwise we
    have to unquote, escape and quote again before returning it.
    The Saml2Client expects the url to be UTF-8 encoded in accordance
    with RFC 3986 and therefore we return it as such.

    :param url: The URL to sanitize
    :return: A sanitized URL

    :type url: string()
    :rtype: string()
    """
    try:
        if url == unquote(url):
            return escape(url, quote = True).encode("UTF-8")
        else:
            return quote(escape(unquote(url), quote = True)).encode("UTF-8")
    except UnicodeDecodeError:
        log.warn('A malicious user tried to crash the application '
                 'by sending non-unicode input in the next parameter')
        raise HTTPBadRequest("Non-unicode input, please try again.")
