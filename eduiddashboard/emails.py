from pyramid.renderers import render

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.verifications import (generate_verification_link,
                                          new_verification_code)
from eduiddashboard.utils import get_short_hash


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

    # Development
    if request.registry.settings.get("development", '') == 'true':
        for mail in mailer.outbox:
            print mail.body
    else:
    mailer.send(message)


def send_termination_mail(request, user):
    mailer = get_mailer(request)
    email = user.get_mail()
    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        'mail': email,
        'displayName': user.get_display_name()
    }

    message = Message(
        subject=_("{site_name} account termination").format(
            site_name=site_name),
        sender=request.registry.settings.get("mail.default_sender"),
        recipients=[email],
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

    mailer.send(message)
