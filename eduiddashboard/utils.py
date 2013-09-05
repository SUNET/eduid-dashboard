from hashlib import sha256


def verify_auth_token(shared_key, public_word, token, generator=sha256):
    return token == generator("{0}{1}".format(shared_key,
                                              public_word)).hexdigest()


def flash(request, message_type, message):
    request.session.flash("{0}|{1}".format(message_type, message))


def get_icon_string(status):
    return "icon-{0}".format(status)


def filter_tab(tabs, remove_tabs):
    return filter(lambda tab: tab['id'] not in remove_tabs, tabs)
