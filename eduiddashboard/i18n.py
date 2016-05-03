from pyramid.i18n import TranslationStringFactory
from eduiddashboard.session import get_session_user

translation_domain = 'eduid-dashboard'
TranslationString = TranslationStringFactory(translation_domain)


def locale_negotiator(request):
    # Import here to avoid circular dependencies
    from eduiddashboard.utils import sanitize_cookies_get

    settings = request.registry.settings
    available_languages = settings['available_languages'].keys()
    cookie_name = settings['lang_cookie_name']

    cookie_lang = sanitize_cookies_get(request, cookie_name, None)
    if cookie_lang and cookie_lang in available_languages:
        return cookie_lang

    user = get_session_user(request, legacy_user = False, raise_on_not_logged_in = False)
    if user:
        preferredLanguage = user.language
        if preferredLanguage:
            return preferredLanguage

    locale_name = request.accept_language.best_match(available_languages)

    if locale_name not in available_languages:
        locale_name = settings.get('default_locale_name', 'sv')
    return locale_name
