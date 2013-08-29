import colander

from eduiddashboard.i18n import TranslationString as _


class EmailUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if 'add' in request.POST:

            emails = request.session.get('user', {}).get('emails')

            for email in emails:
                if value == email['email']:
                    raise colander.Invalid(node, _("This email is already "
                                           "registered in your profile"))
