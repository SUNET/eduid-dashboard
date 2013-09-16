from pyramid.i18n import TranslationStringFactory

translation_domain = 'eduid-dashboard'
TranslationString = TranslationStringFactory(translation_domain)


def locale_negotiator(request):
    settings = request.registry.settings
    available_languages = settings['available_languages']

    user = request.session.get('user')
    if user:
        preferredLanguage = user.get('preferredLanguage', None)
        if preferredLanguage:
            return preferredLanguage

    return request.accept_language.best_match(available_languages)
