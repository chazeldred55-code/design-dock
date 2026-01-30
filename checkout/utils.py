from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_confirmation_email(order):
    """
    Send the user a confirmation email for their order (only once).
    """
    # Prevent duplicate emails
    if getattr(order, "email_sent", False):
        return

    cust_email = order.email

    subject = render_to_string(
        "checkout/confirmation_emails/confirmation_email_subject.txt",
        {"order": order},
    ).strip()

    body = render_to_string(
        "checkout/confirmation_emails/confirmation_email_body.txt",
        {"order": order, "contact_email": settings.DEFAULT_FROM_EMAIL},
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [cust_email],
    )

    # Mark as sent
    order.email_sent = True
    order.save(update_fields=["email_sent"])
