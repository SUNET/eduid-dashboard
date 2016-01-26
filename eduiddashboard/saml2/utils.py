from saml2.config import SPConfig
import imp

from eduid_common.authn.utils import (get_saml2_config, get_location,
                                      get_saml_attribute)
from eduiddashboard import log


def get_saml2_config_from_request(request):
    module_path = request.registry.settings.get('saml2.settings_module')
    return get_saml2_config(module_path)
