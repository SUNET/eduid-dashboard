from pyramid.i18n import TranslationStringFactory

_ = TranslationStringFactory('eduid-dashboard')

def my_view(request):
    return {'project':'eduid-dashboard'}
