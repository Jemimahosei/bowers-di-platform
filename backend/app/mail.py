"""Email sending for campaigns — stdlib smtplib only, no new dependency.

Configuration comes from environment variables (set them in the Render
dashboard — see DEPLOY_NOTES.md):

    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM

When SMTP is not configured, nothing is sent: campaigns stay "queued"
(ready to send) with their content and recipient list visible, and no
email is ever claimed sent. Port 465 uses implicit TLS; any other port
uses STARTTLS when the server offers it.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

CORNELL_DOMAIN = "@cornell.edu"
CORNELL_EMAIL_ERROR = "Use your Cornell email to subscribe"


def is_cornell_email(email: str) -> bool:
    """True when the address is a Cornell address (netid@cornell.edu).

    The newsletter goes to students at the Cornell domain, so public
    signup accepts Cornell addresses only. Staff-imported org contacts
    are vetted by staff instead (see DEPLOY_NOTES.md) and are not
    passed through this check.
    """
    return email.strip().lower().endswith(CORNELL_DOMAIN)


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
                and os.environ.get("SMTP_PASS"))


def smtp_settings() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASS", ""),
        "from_addr": os.environ.get("SMTP_FROM")
        or os.environ.get("SMTP_USER", ""),
    }


def send_email(to_email: str, subject: str, body: str,
               sender_name: str, unsubscribe_url: str) -> None:
    """Send one plain-text email. Raises on failure (caller records it)."""
    cfg = smtp_settings()
    full_body = body.rstrip() + (
        "\n\n—\n"
        f"{sender_name}, Center for Belonging — Cornell Bowers CIS\n"
        "You are receiving this because the Center for Belonging has your "
        "contact information or you signed up for Center updates.\n"
        "To stop receiving these emails, visit: "
        f"{unsubscribe_url}\n"
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{cfg['from_addr']}>"
    msg["To"] = to_email
    msg.set_content(full_body)

    if cfg["port"] == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context,
                              timeout=20) as server:
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        return
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
        server.ehlo()
        try:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        except smtplib.SMTPException:
            # Server does not offer STARTTLS; send in the clear only if
            # the operator configured it that way (local dev relay).
            pass
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)
