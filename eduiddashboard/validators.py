import colander
from copy import copy
import zxcvbn

from pyramid.i18n import get_localizer
from eduid_am.exceptions import UserDoesNotExist, MultipleUsersReturned
from eduid_am.userdb import UserDB

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.vccs import check_password


class OldPasswordValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if not request.registry.settings.get('use_vccs', True):
            return

        old_password = value
        old_password = old_password.replace(" ", "")

        user = request.session['user']
        # Load user from database to ensure we are working on an up-to-date set of credentials.
        user = request.userdb.get_user_by_oid(user['_id'])
        # XXX if we saved user['passwords'] to node.bindings.request['user']['passwords'] here,
        # we could possibly avoid doing the same refresh again when changing passwords
        # (in PasswordsView.save_success()).

        vccs_url = request.registry.settings.get('vccs_url')
        password = check_password(vccs_url, old_password, user)
        if not password:
            err = _('Current password is incorrect')
            localizer = get_localizer(request)
            raise colander.Invalid(node, localizer.translate(err))


class PasswordValidator(object):
    """ Validator which check the security level of the password """

    def __call__(self, node, value):
        request = node.bindings.get('request')
        localizer = get_localizer(request)
        settings = request.registry.settings
        value = value.replace(" ", "")
        password_min_entropy = int(settings.get('password_entropy', 60))

        # We accept a 10% of variance in password_min_entropy because
        # we have calculated the entropy by javascript too and the results
        # may vary.
        password_min_entropy = (0.90 * password_min_entropy)

        generated_password = request.session.get('last_generated_password', '')
        if len(generated_password) > 0 and generated_password == value:
            # Don't validate the password if it is the generated password
            # That is, the user has filled out the form with the suggested
            # password
            return

        veredict = zxcvbn.password_strength(value)

        if veredict.get('entropy', 0) < password_min_entropy:
            err = _('The password complexity is too weak.')
            raise colander.Invalid(node, localizer.translate(err))


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
                                       _("This email address is already in use"))

        elif 'verify' in request.POST or 'setprimary' in request.POST:
            if not request.userdb.exists_by_field('mailAliases.email', value):
                raise colander.Invalid(node,
                                       _("This email address is available"
                                         ))

        elif 'remove' in request.POST:
            email_discovered = False
            for emaildict in request.session['user']['mailAliases']:
                if emaildict['email'] == value:
                    email_discovered = True
                    break
            if not email_discovered:
                raise colander.Invalid(node,
                                       _("Email address does not exist"))

            if len(request.session['user']['mailAliases']) <= 1:
                raise colander.Invalid(node,
                                       _("At least one email is required"))


class EmailExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        try:
            request.userdb.get_user_by_email(value)
        except UserDoesNotExist:
            raise colander.Invalid(node,
                                   _("Email address does not exist"))


class MobilePhoneUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if 'add' in request.POST:
            if request.userdb.exists_by_field('mobile.mobile', value):
                raise colander.Invalid(node,
                                       _("This mobile phone was already registered"))


class EmailOrUsernameExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        is_email = '@' in value
        if not is_email:
            try:
                request.userdb.get_user_by_username(value)
            except UserDB.UserDoesNotExist:
                raise colander.Invalid(node,
                                       _("Username does not exist"))
            except UserDB.MultipleUsersReturned:
                raise colander.Invalid(node,
                                       _("There is more than one user for that username"))
        else:
            try:
                request.userdb.get_user_by_email(value)
            except UserDoesNotExist, e:
                if e.args:
                    msg = e.args[0]
                else:
                    msg = _("email address {} does not exist or is unverified".format(value))
                raise colander.Invalid(node, msg)
            except MultipleUsersReturned:
                raise colander.Invalid(node,
                                       _("There is more than one user for that email"))


class NINExistsValidator(object):

    def __call__(self, node, value):

        from eduiddashboard.models import normalize_nin
        value = normalize_nin(copy(value))
        request = node.bindings.get('request')
        try:
            request.userdb.get_user_by_nin(value)
        except UserDB.UserDoesNotExist:
            raise colander.Invalid(node,
                                   _("This national identity number does not exist, is not verified or is not active"))


class NINUniqueValidator(object):

    def __call__(self, node, value):
        """
            Check if the NIN was not already registered and verified by any user
            Check if the NIN was not already registered by the present user in the
                verifications process.
        """

        from eduiddashboard.models import normalize_nin
        value = normalize_nin(copy(value))

        request = node.bindings.get('request')

        if request.userdb.exists_by_filter({
            'norEduPersonNIN': value,
        }):
            raise colander.Invalid(
                node,
                _("This national identity number is already in use"))

        verifications = request.db.verifications

        if verifications.find({
            'obj_id': value,
            'model_name': 'norEduPersonNIN',
            'verified': False
        }).count() > 0:
            raise colander.Invalid(node, _('This national identity number is already in use'))


class NINReachableValidator(object):

    def __call__(self, node, value):
        """
            Check is the NIN is reachable by eduid_msg service through
            Mina Meddelanden service
        """

        from eduiddashboard.models import normalize_nin

        value = normalize_nin(copy(value))
        request = node.bindings.get('request')
        settings = request.registry.settings
        msg = None
        try:
            reachable = request.msgrelay.nin_reachable(value)
        except request.msgrelay.TaskFailed:
            msg = _('Sorry, we are experiencing temporary technical '
                    'problem with ${service_name}, please try again '
                    'later.')
            reachable = 'Failed'

        if reachable is False:
            msg = _('This national identity number is '
                    'not registered with ${service_name}. Please register '
                    'at <a href="${service_url}">${service_name}</a>.')

        elif reachable is 'Anonymous':
            msg = _('Your registration process with '
                    '${service_name} is not completed. Please visit <a href='
                    '"${service_url}">${service_name}</a> to complete your registration.')

        elif reachable is 'Sender_not':
            msg = _('The ${service_name} service is '
                    'telling us that SUNET (eduID) has been blocked by you. In'
                    ' order to receive a confirmation code from us, you need to'
                    ' accept SUNET (eduID) as a sender at <a href="${service_url}">'
                    '${service_name}</a>.')

        if msg:
            localizer = get_localizer(request)
            raise colander.Invalid(node, localizer.translate(msg, mapping={
                'service_name': settings.get('nin_service_name'),
                'service_url': settings.get('nin_service_url'),
            }))


class ResetPasswordCodeExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        if not request.db.reset_passwords.find_one({'hash_code': value}):
            raise colander.Invalid(node,
                                   _("The entered code does not exist"))
