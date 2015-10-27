from pyramid.i18n import TranslationStringFactory

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

    user = request.session.get('user')
    if user:
        preferredLanguage = user.get_preferred_language()
        if preferredLanguage:
            return preferredLanguage

    locale_name = request.accept_language.best_match(available_languages)

    if locale_name not in available_languages:
        locale_name = settings.get('default_locale_name', 'sv')
    return locale_name
