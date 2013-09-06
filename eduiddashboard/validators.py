import colander

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.vccs import check_password


PASSWORD_MIN_LENGTH = 5


class OldPasswordValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        old_password = value
        password = check_password(old_password, request)
        if not password:
            err = _('Old password do not match')
            raise colander.Invalid(node, err)


class PasswordValidator(object):
    """ Validator which check the security level of the password """

    def __call__(self, node, value):
        if len(value) < PASSWORD_MIN_LENGTH:
            err = _('"${val}" has to be more than ${len} characters length',
                    mapping={'val':value, 'len':PASSWORD_MIN_LENGTH})
            raise colander.Invalid(node, err)


class EmailUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if 'add' in request.POST:
            if request.userdb.exists_by_field('mailAliases.mail', value):
                raise colander.Invalid(node,
                                       _("This email is already registered"))

        elif 'verify' in request.POST or 'setprimary' in request.POST:
            if not request.userdb.exists_by_field('mailAliases.mail', value):
                raise colander.Invalid(node,
                                       _("This email is not registered already"
                                         ))

        elif 'remove' in request.POST:
            email_discovered = False
            for emaildict in request.session['user']['mailAliases']:
                if emaildict['email'] == value:
                    email_discovered = True
                    break
            if not email_discovered:
                raise colander.Invalid(node,
                                       _("The email can't be found"))

            if len(request.session['user']['mailAliases']) <= 1:
                raise colander.Invalid(node,
                                       _("At least one email is required"))
