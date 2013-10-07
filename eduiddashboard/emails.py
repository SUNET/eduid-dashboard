from pyramid.renderers import render

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.verifications import generate_verification_link


def send_verification_mail(request, email):
    mailer = get_mailer(request)
    verification_link = generate_verification_link(request, request.db,
                                                   'email', email)

    site_name = request.registry.settings.get("site.name", "eduID")

    context = {
        "email": email,
        "verification_link": verification_link,
        "site_url": request.context.safe_route_url("home"),
        "site_name": site_name,
    }

    message = Message(
        subject=_("{site_name} verification email").format(
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

    mailer.send(message)
