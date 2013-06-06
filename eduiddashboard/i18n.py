from pyramid.i18n import TranslationStringFactory

translation_domain = 'eduid-dashboard'
TranslationString = TranslationStringFactory(translation_domain)


def locale_negotiator(request):
    available_languages = request.registry.settings['available_languages']
    return request.accept_language.best_match(available_languages)
