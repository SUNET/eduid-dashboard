import colander

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.vccs import check_password


PASSWORD_MIN_LENGTH = 5


class OldPasswordValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        old_password = value
        user = request.session['user']

        vccs_url = request.registry.settings.get('vccs_url')
        password = check_password(vccs_url, old_password, user)
        if not password:
            err = _('Current password is incorrect')
            raise colander.Invalid(node, err)


class PasswordValidator(object):
    """ Validator which check the security level of the password """

    def __call__(self, node, value):
        if len(value) < PASSWORD_MIN_LENGTH:
            err = _('The password is too short, minimum length is ${len}',
                    mapping={'len': PASSWORD_MIN_LENGTH})
            raise colander.Invalid(node, err)


class PermissionsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        available_permissions = request.registry.settings.get('available_permissions')
        for item in value:
            if item not in available_permissions:
                raise colander.Invalid(
                    node,
                    _('The permission selected is not available')
                )


class EmailUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if 'add' in request.POST:
            if request.userdb.exists_by_field('mailAliases.email', value):
                raise colander.Invalid(node,
                                       _("This email is already registered"))

        elif 'verify' in request.POST or 'setprimary' in request.POST:
            if not request.userdb.exists_by_field('mailAliases.email', value):
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


class EmailExistsValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')
        if not request.userdb.exists_by_field('mailAliases.email', value):
            raise colander.Invalid(node,
                                   _("This email does not exist"))


class NINUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')
        nin_filter = {
            'norEduPersonNIN.norEduPersonNIN': value,
            'norEduPersonNIN.verified': True,
        }
        if request.userdb.exists_by_filter(nin_filter):
            raise colander.Invalid(node,
                _("This NIN is already registered and was verified by other user"))
        user = request.context.get_user()
        nin_exist = len([x for x in user.get('norEduPersonNIN', []) if x['norEduPersonNIN'] == value]) > 0
        if nin_exist:
            raise colander.Invalid(node,
                _("This NIN is already registered in your NIN list"))
