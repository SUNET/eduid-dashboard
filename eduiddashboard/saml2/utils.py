from saml2.config import SPConfig
import imp


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
