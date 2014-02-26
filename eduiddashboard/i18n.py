from pyramid.i18n import TranslationStringFactory
from eduid_am.user import User

translation_domain = 'eduid-dashboard'
TranslationString = TranslationStringFactory(translation_domain)


def locale_negotiator(request):
    settings = request.registry.settings
    available_languages = settings['available_languages'].keys()
    cookie_name = settings['lang_cookie_name']

    cookie_lang = request.cookies.get(cookie_name, None)
    if cookie_lang and cookie_lang in available_languages:
        return cookie_lang

    user = request.session.get('user')
    if user:
        preferredLanguage = user.get_preferred_language()
        if preferredLanguage:
            return preferredLanguage

    return request.accept_language.best_match(available_languages)
