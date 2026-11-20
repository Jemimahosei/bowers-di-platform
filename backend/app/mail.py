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


def _send_message(msg: EmailMessage) -> None:
    """Deliver one already-built message via the configured SMTP server.

    Port 465 uses implicit TLS; any other port uses STARTTLS when the
    server offers it. Raises on failure (caller records it)."""
    cfg = smtp_settings()
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


def send_email(to_email: str, subject: str, body: str,
               sender_name: str, unsubscribe_url: str) -> None:
    """Send one plain-text campaign email. Raises on failure (caller records it)."""
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
    _send_message(msg)


def send_confirmation_email(to_email: str, name: str,
                            confirmation_url: str) -> None:
    """Send the double-opt-in confirmation email for a newsletter signup.

    This is the confirmation channel: the link lives in this email, not
    on a page. Raises on failure — the caller falls back to showing the
    link on /newsletter only instead of pretending the email went out.
    """
    cfg = smtp_settings()
    greeting = f"Hi {name}," if name else "Hi there,"
    # Plain ASCII on purpose: a UTF-8 body gets quoted-printable
    # encoding, which folds long lines at 76 chars — and the
    # confirmation URL is long enough to be split mid-token, which
    # breaks the link for anyone who copies it. ASCII stays 7bit and
    # the URL line goes out whole.
    body = (
        f"{greeting}\n\n"
        "You signed up for the Center for Belonging newsletter - "
        "thanks for joining.\n\n"
        "Please confirm your subscription by clicking this link:\n"
        f"{confirmation_url}\n\n"
        "Every issue brings you real resources from the Center, plus "
        "opportunities - conference funding and deadlines, scholarships "
        "and paid opportunities, events and programs. It keeps coming, "
        "so you don't have to go looking for it.\n\n"
        "If you didn't sign up, you can ignore this email - nothing "
        "else will be sent.\n"
    )
    msg = EmailMessage()
    msg["Subject"] = "Confirm your subscription to the Center for Belonging newsletter"
    msg["From"] = f"Center for Belonging <{cfg['from_addr']}>"
    msg["To"] = to_email
    # cte="7bit" (with the ASCII-only body above): the default utf-8
    # charset would pick quoted-printable and fold the URL line again.
    msg.set_content(body, cte="7bit")
    _send_message(msg)
