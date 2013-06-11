

FLASH_SEPARATOR = '|'


def get_flash_message_type(message):
    return message.split(FLASH_SEPARATOR)[0]


def get_flash_message_text(message):
    return message.split(FLASH_SEPARATOR)[1]
