import pycountry
from pyramid.threadlocal import get_current_request

FLASH_SEPARATOR = '|'


def get_flash_message_type(message):
    typ = message.split(FLASH_SEPARATOR)[0]
    if typ == 'error':
        return 'danger'
    return typ


def get_flash_message_text(message):
    return message.split(FLASH_SEPARATOR)[1]


def address_type_text(value):
    from eduiddashboard.models import POSTAL_ADDRESS_TYPES
    return dict(POSTAL_ADDRESS_TYPES)[value]


def country_name(value):
    return pycountry.countries.get(alpha2=value).name


def context_route_url(value):
    request = get_current_request()
    return request.context.route_url(value)


def safe_context_route_url(value):
    request = get_current_request()
    return request.context.route_url(value)
