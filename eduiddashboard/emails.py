from pyramid.renderers import render

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.verifications import (generate_verification_link,
                                          new_verification_code)
from eduiddashboard.utils import get_short_hash
from eduiddashboard import log


def send_verification_mail(request, email, reference=None, code=None):
    mailer = get_mailer(request)
    if code is None or reference is None:
        reference, code = new_verification_code(request, 'mailAliases', email, request.context.user,
                                     hasher=get_short_hash)

    verification_link = generate_verification_link(request, code,
                                                   'mailAliases')

    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "email": email,
        "verification_link": verification_link,
        "site_url": request.context.safe_route_url("home"),
        "site_name": site_name,
        "code": code,
    }

    message = Message(
        subject=_("{site_name} confirmation email").format(
            site_name=site_name),
        sender=request.registry.settings.get("mail.default_sender"),
        recipients=[email],
        body=render(
            "templates/verification_email.txt.jinja2",
            context,
            request,
        ),
        html=render(
            "templates/verification_email.html.jinja2",
            context,
            request,
        ),
    )

    # DEBUG
    if request.registry.settings.get('developer_mode', False):
        log.debug(message.body)
    else:
        mailer.send(message)
    log.debug("Sent verification mail to user {!r} with address {!s}.".format(request.context.user, email))
    request.stats.count('dashboard/email_send_verification_code', 1)


def send_termination_mail(request, user):
    mailer = get_mailer(request)
    support_email = request.registry.settings.get('mail.support_email', 'support@eduid.se')
    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        'support_mail': support_email,
        'displayName': user.display_name
    }

    if user.mail_addresses.primary is not None:
        address = user.mail_addresses.primary.key
    elif user.mail_addresses.count > 0:
        for a in user.mail_addresses.to_list():
            address = a.key
            break
    else:
        log.info('User {} has no email address, not possible to send a message'.format(user.eppn))
        return

    message = Message(
        subject=_("{site_name} account termination").format(
            site_name=site_name),
        sender=request.registry.settings.get("mail.default_sender"),
        recipients=[address],
        body=render(
            "templates/termination_email.txt.jinja2",
            context,
            request,
        ),
        html=render(
            "templates/termination_email.html.jinja2",
            context,
            request,
        ),
    )

    # DEBUG
    if request.registry.settings.get('developer_mode', False):
        log.debug(message.body)
    else:
        mailer.send(message)
    log.debug("Sent termination mail to user {!r} with address {!s}.".format(
        user, address))
    request.stats.count('dashboard/email_send_termination_mail', 1)


def send_reset_password_mail(request, user, reset_password_link, has_mobile=False):
    """ Send an email with the instructions for resetting password """

    if user.mail_addresses.primary is not None:
        email = user.mail_addresses.primary.key
    elif user.mail_addresses.count > 0:
        for a in user.mail_addresses.to_list():
            email = a.key
            break
    else:
        log.info('User {} has no email address, not possible to send a message'.format(user.eppn))
        return
    mailer = get_mailer(request)

    site_name = request.registry.settings.get("site.name", "eduID")
    password_reset_timeout = int(request.registry.settings.get("password_reset_timeout", "2880")) / 60
    reset_offset = int(request.registry.settings.get("password_reset_email_mobile_offset", "1440")) / 60

    context = {
        "email": email,
        "reset_password_link": reset_password_link,
        "password_reset_timeout": password_reset_timeout,
        "site_url": request.route_url("home"),
        "site_name": site_name,
        "has_mobile": has_mobile,
        "password_reset_email_mobile_offset": reset_offset,
    }

    message = Message(
        subject=_("Reset your {site_name} password").format(
            site_name=site_name),
        sender=request.registry.settings.get("mail.default_sender"),
        recipients=[email],
        body=render(
            "templates/reset-password-email.txt.jinja2",
            context,
            request,
        ),
        html=render(
            "templates/reset-password-email.html.jinja2",
            context,
            request,
        ),
    )

    # DEBUG
    if request.registry.settings.get('developer_mode', False):
        log.debug(message.body)
    else:
        mailer.send(message)
    log.debug("Sent reset password mail to user {!r} with address {!s}.".format(user, email))
    request.stats.count('dashboard/email_send_pwreset_mail', 1)

