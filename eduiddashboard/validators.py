import colander
from copy import copy
import zxcvbn

from pyramid.i18n import get_localizer
from eduid_userdb.exceptions import UserDoesNotExist, MultipleUsersReturned
from eduid_userdb.userdb import UserDB

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.vccs import check_password
from eduiddashboard.utils import (normalize_to_e_164,
                                  sanitize_input,
                                  sanitize_post_key)
from eduiddashboard.session import get_session_user
from eduiddashboard.idproofinglog import TeleAdressProofing, TeleAdressProofingRelation
from eduiddashboard import log


class OldPasswordValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')

        if not request.registry.settings.get('use_vccs', True):
            return

        old_password = value.replace(" ", "")

        user = get_session_user(request)

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

        # Get a users e-mail addresses to make sure a user does not use one of those as password
        user = get_session_user(request, raise_on_not_logged_in = False)
        if not user:
            # User is resetting a forgotten password
            hash_code = request.matchdict['code']
            password_reset = request.db.reset_passwords.find_one({'hash_code': hash_code})
            user = request.userdb_new.get_user_by_mail(password_reset['email'])
        mail_addresses = [item.email for item in user.mail_addresses.to_list()]

        veredict = zxcvbn.password_strength(value, user_inputs=mail_addresses)

        if veredict.get('entropy', 0) < password_min_entropy:
            err = _('The password complexity is too weak.')
            raise colander.Invalid(node, localizer.translate(err))


class PermissionsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        available_permissions = request.registry.settings.get('available_permissions')
        for item in value:
            if item not in available_permissions:
                err = _('The permission selected is not available')
                raise colander.Invalid(
                    node,
                    get_localizer(request).translate(err)
                )


class MaliciousInputValidator(object):

    def __call__(self, node, value):
        """
        Check the input for potentially harmful content
        """
        request = node.bindings.get('request')
        localizer = get_localizer(request)

        if value != sanitize_input(value, strip_characters=True):
            err = _("Some of the characters you entered are "
                    "not allowed, please try again.")
            raise colander.Invalid(node, localizer.translate(err))


class EmailUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')
        user = get_session_user(request)
        user_emails = [e.email for e in user.mail_addresses.to_list()]
        if user.mail_addresses.primary:
            user_emails.append(user.mail_addresses.primary.email)
        localizer = get_localizer(request)

        if sanitize_post_key(request, 'add') is not None:
            if value in user_emails:
                err = _("You already have this email address")
                raise colander.Invalid(node, localizer.translate(err))

        elif set(['verify', 'setprimary', 'remove']).intersection(set(request.POST)):
            if value not in user_emails:
                err = _("This email address is unavailable")
                raise colander.Invalid(node, localizer.translate(err))


class EmailExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        try:
            request.userdb.get_user_by_email(value)
        except UserDoesNotExist:
            err = _("Email address does not exist")
            raise colander.Invalid(node, get_localizer(request).translate(err))


class MobilePhoneUniqueValidator(object):

    def __call__(self, node, value):

        request = node.bindings.get('request')
        user = get_session_user(request)
        mobile = normalize_to_e_164(request, value)
        if sanitize_post_key(request, 'add') is not None:
            if user.phone_numbers.find(mobile):
                err = _("This mobile phone was already registered")
                raise colander.Invalid(node, get_localizer(request).translate(err))


class EmailOrUsernameExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        is_email = '@' in value
        localizer = get_localizer(request)
        if not is_email:
            try:
                request.userdb.get_user_by_username(value)
            except UserDB.UserDoesNotExist:
                err = _("Username does not exist")
                raise colander.Invalid(node, localizer.translate(err))
            except UserDB.MultipleUsersReturned:
                err = _("There is more than one user for that username")
                raise colander.Invalid(node, localizer.translate(err))
        else:
            try:
                request.userdb.get_user_by_email(value)
            except UserDoesNotExist as e:
                if e.args:
                    msg = e.args[0]
                else:
                    msg = _("email address ${val} does not exist "
                            "or is unverified")
                    msg = localizer.translate(msg, mapping={'val': value})
                raise colander.Invalid(node, msg)
            except MultipleUsersReturned:
                msg = _("There is more than one user for that email")
                raise colander.Invalid(node, localizer.translate(msg))


class NINExistsValidator(object):

    def __call__(self, node, value):

        from eduiddashboard.models import normalize_nin
        value = normalize_nin(copy(value))
        request = node.bindings.get('request')
        try:
            request.userdb.get_user_by_nin(value)
        except UserDB.UserDoesNotExist:
            err = _("This national identity number does not exist, "
                    "is not verified or is not active")
            raise colander.Invalid(node, get_localizer(request).translate(err))


class NINUniqueValidator(object):

    def __call__(self, node, value):
        """
        Validator which makes sure that:
        1. the NiN has not already been added by the user
        2. the user does not already have a confirmed NiN.
        """

        from eduiddashboard.models import normalize_nin
        value = normalize_nin(copy(value))

        request = node.bindings.get('request')
        user = get_session_user(request)
        user_nins = user.nins

        unverified_user_nins = request.db.verifications.find({
            'obj_id': value,
            'model_name': 'norEduPersonNIN',
            'user_oid': user.user_id,
            'verified': False
        })

        # Search the request.POST for any post that starts with "add".
        for post_value in request.POST:
            if post_value.startswith('add') and (user_nins.find(value) or
                                      unverified_user_nins.count() > 0):
                err = _('National identity number already added')
                raise colander.Invalid(node, get_localizer(request).translate(err))

            elif post_value.startswith('add') and user_nins.count > 0:
                err = _('You already have a confirmed national identity number')
                raise colander.Invalid(node, get_localizer(request).translate(err))


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

        if settings.get('developer_mode', False):
            return
        
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
                    'not registered with "${service_name}". Please register '
                    'at <a href="${service_url}" target="_blank">${service_name}</a>.')

        elif reachable is 'Anonymous':
            msg = _('Your registration process with '
                    '"${service_name}" is not complete. Please visit <a href='
                    '"${service_url}" target="_blank">${service_name}</a> to complete your registration.')

        elif reachable is 'Sender_not':
            msg = _('According to "${service_name}"'
                    ' you have opted out to receive messages from SUNET (eduID). In'
                    ' order to receive a confirmation code from us, you need to'
                    ' accept SUNET (eduID) as a sender at <a href="${service_url}" target="_blank">'
                    '${service_name}</a>.')

        if msg:
            localizer = get_localizer(request)
            raise colander.Invalid(node, localizer.translate(msg, mapping={
                'service_name': settings.get('nin_service_name'),
                'service_url': settings.get('nin_service_url'),
            }))


def _get_age(nin):
    import time

    current_year = int(time.strftime("%Y"))
    current_month = int(time.strftime("%m"))
    current_day = int(time.strftime("%d"))

    birth_year = int(nin[:4])
    birth_month = int(nin[4:6])
    birth_day = int(nin[6:8])

    age = current_year - birth_year

    if current_month < birth_month or (current_month == birth_month and current_day < birth_day):
        age -= 1

    return age


def validate_nin_by_mobile(request, user, nin):
    """

    :param request:
    :param user: eduid_userdb.User
    :param nin:
    :return:
    """
    log.info('Trying to verify nin via mobile number for user {!r}.'.format(user))
    log.debug('NIN: {!s}.'.format(nin))
    from eduid_lookup_mobile.utilities import format_NIN
    # Get list of verified mobile numbers
    verified_mobiles = [x.number for x in user.phone_numbers.to_list() if x.is_verified]

    national_identity_number = format_NIN(nin)
    status = 'no_phone'
    valid_mobile = None
    registered_to_nin = None

    age = _get_age(national_identity_number)

    try:
        for mobile_number in verified_mobiles:
            status = 'no_match'
            # Get the registered owner of the mobile number
            registered_to_nin = request.lookuprelay.find_NIN_by_mobile(mobile_number)
            registered_to_nin = format_NIN(registered_to_nin)

            if registered_to_nin == national_identity_number:
                # Check if registered nin was the given nin
                valid_mobile = mobile_number
                status = 'match'
                log.info('Mobile number matched for user {!r}.'.format(user))
                log.debug('Mobile {!s} registered to NIN: {!s}.'.format(valid_mobile, registered_to_nin))
                request.stats.count('dashboard/validate_nin_by_mobile_exact_match', 1)
                break
            elif registered_to_nin is not None and age < 18:
                # Check if registered nin is related to given nin
                relation = request.msgrelay.get_relations_to(national_identity_number, registered_to_nin)
                # TODO All relations?
                #valid_relations = ['M', 'B', 'FA', 'MO', 'VF']
                valid_relations = ['FA', 'MO']
                if any(r in relation for r in valid_relations):
                    valid_mobile = mobile_number
                    status = 'match_by_navet'
                    log.info('Mobile number matched for user {!r} via navet.'.format(user))
                    log.debug('Mobile {!s} registered to NIN: {!s}.'.format(valid_mobile, registered_to_nin))
                    log.debug('Person with NIN {!s} have relation {!s} to user: {!r}.'.format(registered_to_nin,
                                                                                              relation, user))
                    request.stats.count('dashboard/validate_nin_by_mobile_relative_match', 1)
                    break
    except request.lookuprelay.TaskFailed:
        status = 'error_lookup'
    except request.msgrelay.TaskFailed:
        status = 'error_navet'

    msg = None
    if status == 'no_phone':
        msg = _('You have no confirmed mobile phone')
        log.info('User {!r} has no verified mobile phone number.'.format(user))
    elif status == 'no_match':
        log.info('User {!r} NIN is not associated with any verified mobile phone number.'.format(user))
        msg = _('The given mobile number was not associated to the given national identity number')
        request.stats.count('dashboard/validate_nin_by_mobile_no_match', 1)
    elif status == 'error_lookup' or status == 'error_navet':
        log.error('Validate NIN via mobile failed with status "{!s}" for user {!r}.'.format(status, user))
        msg = _('Sorry, we are experiencing temporary technical '
                'problem with ${service_name}, please try again '
                'later.')
        request.stats.count('dashboard/validate_nin_by_mobile_error', 1)

    if status == 'match' or status == 'match_by_navet':
        log.info('Validate NIN via mobile succeeded with status "{!s}" for user {!r}.'.format(status, user))
        msg = _('Validate NIN via mobile with succeeded')
        user_postal_address = request.msgrelay.get_full_postal_address(national_identity_number)
        if status == 'match':
            proofing_data = TeleAdressProofing(user, status, national_identity_number, valid_mobile,
                                               user_postal_address)
        else:
            registered_postal_address = request.msgrelay.get_full_postal_address(registered_to_nin)
            proofing_data = TeleAdressProofingRelation(user, status, national_identity_number, valid_mobile,
                                                       user_postal_address, registered_to_nin, relation,
                                                       registered_postal_address)

        log.info('Logging of mobile proofing data for user {!r}.'.format(user))
        if not request.idproofinglog.log_verification(proofing_data):
            log.error('Logging of mobile proofing data for user {!r} failed.'.format(user))
            valid_mobile = None
            msg = _('Sorry, we are experiencing temporary technical '
                    'problem with ${service_name}, please try again '
                    'later.')

    validation_result = {'success': valid_mobile is not None, 'message': msg, 'mobile': valid_mobile}
    return validation_result

class NINRegisteredMobileValidator(object):
    """ Validator that checks so the primary mobile number is registered on the given national identity number """

    def __call__(self, node, value):
        request = node.bindings.get('request')
        settings = request.registry.settings
        user = get_session_user(request)
        result = validate_nin_by_mobile(request, user, value)

        if not result['success']:
            localizer = get_localizer(request)
            raise colander.Invalid(node, localizer.translate(result['message'], mapping={
                'service_name': settings.get('mobile_service_name', 'TeleAdress'),
            }))

class ResetPasswordCodeExistsValidator(object):

    def __call__(self, node, value):
        request = node.bindings.get('request')
        if not request.db.reset_passwords.find_one({'hash_code': value}):
            err = _("The entered code does not exist")
            raise colander.Invalid(node, get_localizer(request).translate(err))


class CSRFTokenValidator(object):
    """
    Validator that verify that a form submission contains a valid CSRF token
    to foil cross-site request forgery attacks.
    """
    def __call__(self, node, value):
        request = node.bindings.get('request')
        token = request.session.get_csrf_token()

        if value != token:
            log.debug("CSRF token validation failed: Form {!r} != Session {!r}".format(value, token))
            err = _("Invalid CSRF token")
            raise colander.Invalid(node, get_localizer(request).translate(err))


class ResetPasswordFormValidator(colander.All):
    """
    Succeed if at least one of its subvalidators does not raise an exception.
    """
    def __call__(self, node, value):
        try:
            return super(ResetPasswordFormValidator, self).__call__(node, value)
        except colander.Invalid as e:
            if len(e.msg) < len(self.validators):
                # At least one validator did not fail:
                return
            request = node.bindings.get('request')
            err = _("Valid input formats are:<ul>"
                    "<li>National identity number: yyyymmddnnnn</li>"
                    "<li>Mobile phone number that begin with + or 07</li>"
                    "<li>E-mail address: user@example.edu</li></ul>")
            raise colander.Invalid(node, get_localizer(request).translate(err))
