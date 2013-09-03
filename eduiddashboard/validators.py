from bson import ObjectId

import colander

import vccs_client

from eduiddashboard.i18n import TranslationString as _


PASSWORD_MIN_LENGTH = 5


@colander.deferred
def old_password_validator(node, kw):
    request = kw['request']
    return OldPasswordValidator(request)


class OldPasswordValidator(object):

    def __init__(self, request):
        self.user_email = request.session['mail']
        self.request = request

    def __call__(self, node, value):
        old_password = value
        password_id = ObjectId()
        vccs = vccs_client.VCCSClient(
            base_url=self.request.registry.settings.get('vccs_url'),
        )
        old_factor = vccs_client.VCCSPasswordFactor(old_password,
                                                    credential_id=str(password_id))
        # XXX: Next line always returns a unknown 500 error
        if not vccs.authenticate(self.user_email, [old_factor]):
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

        if 'verify' in request.POST:
            if not request.userdb.exists_by_field('mailAliases.mail', value):
                raise colander.Invalid(node,
                                       _("This email is not registered already"
                                         ", so you can not very it"))

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
