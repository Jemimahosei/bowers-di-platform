"""Email sending for campaigns — SMTP or Resend, stdlib only, no new dependency.

Configuration comes from environment variables (set them in the Render
dashboard — see DEPLOY_NOTES.md). Senders, in priority order:

1. SMTP (SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS,
   SMTP_FROM) when fully configured. Port 465 uses implicit TLS; any
   other port uses STARTTLS when the server offers it.
2. Resend (https://resend.com) when RESEND_API_KEY is set — a plain
   HTTPS POST to https://api.resend.com/emails. This is the sender
   that works on Render's free tier: Render blocks outbound SMTP
   ports (25/465/587), so SMTP cannot send from the live deploy. The
   sender address comes from RESEND_FROM (default
   "Center for Belonging <hello@jemimahosei.com>" — jemimahosei.com
   is the domain verified in Resend).

When neither is configured, nothing is sent: campaigns stay "queued"
(ready to send) with their content and recipient list visible, and a
newsletter signup falls back to the /newsletter-only confirmation
link — no email is ever claimed sent.

``email_mode()`` reports which sender is active ('smtp' | 'resend' |
'console') and ``last_error()`` the last send failure, for
``GET /api/health``. ``send_email`` / ``send_welcome_email``
raise on failure — the caller records it (per-recipient status on
campaigns, fallback link on signup).
"""

import json
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

CORNELL_DOMAIN = "@cornell.edu"
CORNELL_EMAIL_ERROR = "Use your Cornell email to subscribe"

DEFAULT_RESEND_FROM = "Center for Belonging <hello@jemimahosei.com>"

# The last send failure, for /api/health. Never holds a secret: the API
# key is sent only as an Authorization header and is never interpolated
# into any recorded detail.
LAST_ERROR = {"detail": ""}


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


def resend_configured() -> bool:
    return bool((os.environ.get("RESEND_API_KEY") or "").strip())


def email_configured() -> bool:
    """True when any sender is configured (SMTP or Resend)."""
    return smtp_configured() or resend_configured()


def email_mode() -> str:
    """'smtp' when SMTP is set, 'resend' when a Resend key is set, else 'console'."""
    if smtp_configured():
        return "smtp"
    return "resend" if resend_configured() else "console"


def last_error() -> str:
    """The last send failure ("" when the last send succeeded or none was tried)."""
    return LAST_ERROR["detail"]


def _record_failure(detail: str) -> None:
    LAST_ERROR["detail"] = detail[:300]


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


def _resend_from(sender_name: str) -> str:
    """The From header for a Resend send.

    RESEND_FROM as set (usually "Name <addr@domain>"); a bare address
    is wrapped with the sender's display name."""
    raw = (os.environ.get("RESEND_FROM") or DEFAULT_RESEND_FROM).strip()
    if "<" in raw:
        return raw
    return f"{sender_name} <{raw}>"


def _send_resend(to_email: str, subject: str, text: str,
                 sender_name: str, html: str | None = None) -> None:
    """Deliver one message via Resend. Raises on failure.

    The API key travels only in the Authorization header and is never
    included in the recorded error detail."""
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    payload_dict = {
        "from": _resend_from(sender_name),
        "to": [to_email],
        "subject": subject,
        "text": text,
    }
    if html:
        payload_dict["html"] = html
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Resend sits behind Cloudflare, which refuses Python's
            # default User-Agent with error 1010.
            "User-Agent": "opendoor/1.0 "
                          "(+https://bowers-di-platform.onrender.com)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        try:
            reason = exc.read().decode(errors="replace")[:200]
        except Exception:  # noqa: BLE001 - already failing
            reason = ""
        _record_failure(f"Resend answered {exc.code}: {reason}")
        raise
    except Exception as exc:  # noqa: BLE001 - record, then raise
        _record_failure(f"{type(exc).__name__}: {exc}")
        raise
    LAST_ERROR["detail"] = ""


def _send_text(to_email: str, subject: str, text: str, sender_name: str,
               smtp_from: str, cte: str | None = None,
               html: str | None = None) -> None:
    """Send one message via the configured sender.

    SMTP builds an EmailMessage (``cte`` picks the transfer encoding —
    "7bit" for the confirmation email, so the long URL is never
    folded); Resend posts the parts as-is. When ``html`` is given it
    travels as the HTML alternative alongside the plain text. Raises
    on failure — the caller records it."""
    if smtp_configured():
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{smtp_from}>"
        msg["To"] = to_email
        if cte is not None:
            msg.set_content(text, cte=cte)
        else:
            msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        try:
            _send_message(msg)
        except Exception as exc:  # noqa: BLE001 - record, then raise
            _record_failure(f"SMTP failed: {type(exc).__name__}: {exc}")
            raise
        LAST_ERROR["detail"] = ""
        return
    if resend_configured():
        _send_resend(to_email, subject, text, sender_name, html)
        return
    _record_failure("No email sender configured")
    raise RuntimeError("No email sender configured")


def send_email(to_email: str, subject: str, body: str,
               sender_name: str, unsubscribe_url: str,
               html_body: str | None = None) -> None:
    """Send one campaign email. Raises on failure (caller records it).

    ``body`` is the plain-text part (footer appended here);
    ``html_body``, when given, is the complete HTML alternative —
    it carries its own footer and unsubscribe link."""
    cfg = smtp_settings()
    full_body = body.rstrip() + (
        "\n\n—\n"
        f"{sender_name}, Center for Belonging — Cornell Bowers CIS\n"
        "You are receiving this because the Center for Belonging has your "
        "contact information or you signed up for Center updates.\n"
        "To stop receiving these emails, visit: "
        f"{unsubscribe_url}\n"
    )
    _send_text(to_email, subject, full_body, sender_name,
               cfg["from_addr"], html=html_body)


def send_welcome_email(to_email: str, name: str,
                       unsubscribe_url: str) -> None:
    """Send the welcome note for a newsletter signup.

    Single opt-in (Jemimah, 2026-11-22): signing up subscribes the
    address immediately — there is no confirmation link or second
    step. This email is simply the short note that says so. Raises on
    failure; the subscription stands either way, so the caller just
    reports that the note did not go out.
    """
    cfg = smtp_settings()
    greeting = f"Hi {name}," if name else "Hi there,"
    # Plain ASCII on purpose (see git history): it keeps the SMTP
    # path on 7bit encoding so the unsubscribe URL is never folded.
    body = (
        f"{greeting}\n\n"
        "You're subscribed - welcome to Open Door, the Center for "
        "Belonging newsletter at Cornell Bowers CIS.\n\n"
        "You are now officially on the list. Every issue brings you "
        "real resources from the Center, plus opportunities - "
        "conference funding and deadlines, scholarships and paid "
        "opportunities, events and programs - straight to this inbox. "
        "There is nothing else you need to do.\n\n"
        "If you ever want to stop receiving it, unsubscribe here:\n"
        f"{unsubscribe_url}\n"
    )
    _send_text(
        to_email,
        "You're subscribed - welcome to Open Door",
        body, "Center for Belonging", cfg["from_addr"], cte="7bit")


def send_booking_confirmation_email(to_email: str, name: str,
                                    when_label: str, slot_type: str,
                                    host: str) -> None:
    """Send the confirmation email for a booked time with the host.

    The booking flow has always told students "a confirmation is on
    its way" — this is the email that promise refers to. Raises on
    failure; the caller (book_slot) treats a failure as non-fatal so
    a mail problem can never lose a booking. Plain ASCII / 7bit like
    the newsletter confirmation.
    """
    cfg = smtp_settings()
    greeting = f"Hi {name}," if name else "Hi there,"
    kind = "in person" if slot_type == "in-person" else "by phone/video call"
    body = (
        f"{greeting}\n\n"
        f"Your time with {host} is booked.\n\n"
        f"When: {when_label} ({kind})\n\n"
        "If you need to change or cancel, just reply to this email.\n\n"
        "Center for Belonging, Cornell Bowers CIS\n"
    )
    _send_text(
        to_email,
        f"Your booking with {host} is confirmed",
        body, "Center for Belonging", cfg["from_addr"], cte="7bit")
