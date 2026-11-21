"""Resend sender checks for app.mail (mocked HTTP — nothing is really sent).

Covers the Resend path added Nov 21, 2026: with RESEND_API_KEY set and
no SMTP, the confirmation email POSTs to api.resend.com with the right
headers; with neither set, email is unconfigured; a Resend HTTP error
is recorded in last_error() and raised to the caller.

Run from backend/ (stdlib unittest, no extra dependency):

    python3 -m unittest test_mail_resend -v
"""

import io
import json
import os
import smtplib
import unittest
import urllib.error
import urllib.request
from unittest import mock

import app.mail as mail

LONG_TOKEN = "x" * 90
CONFIRM_URL = (
    "https://bowers-di-platform.onrender.com/newsletter?token=" + LONG_TOKEN
)

EMAIL_VARS = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM",
    "RESEND_API_KEY", "RESEND_FROM",
)


class _FakeResponse:
    """Minimal urlopen response: a context manager with read()."""

    def __init__(self, body=b'{"id": "re_test"}'):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeSMTP:
    """Captures what _send_message would deliver over SMTP."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.sent = []
        _FakeSMTP.instances.append(self)

    def ehlo(self):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        self.sent.append(msg)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class MailResendTests(unittest.TestCase):
    def setUp(self):
        self._saved_env = dict(os.environ)
        for key in EMAIL_VARS:
            os.environ.pop(key, None)
        mail.LAST_ERROR["detail"] = ""
        _FakeSMTP.instances.clear()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        mail.LAST_ERROR["detail"] = ""

    def _capture_urlopen(self, response=None):
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req)
            return _FakeResponse(response)

        patcher = mock.patch.object(urllib.request, "urlopen",
                                    side_effect=fake_urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls

    def test_confirmation_via_resend_posts_to_api(self):
        """(a) RESEND_API_KEY set, no SMTP: POSTs to api.resend.com."""
        os.environ["RESEND_API_KEY"] = "re_test_key_123"
        calls = self._capture_urlopen()
        mail.send_confirmation_email("abc123@cornell.edu", "Test Person",
                                     CONFIRM_URL)
        self.assertEqual(len(calls), 1)
        req = calls[0]
        self.assertEqual(req.full_url, "https://api.resend.com/emails")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"),
                         "Bearer re_test_key_123")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        ua = req.get_header("User-agent") or ""
        self.assertIn("bowers-di-platform", ua)
        self.assertNotIn("Python-urllib", ua)
        payload = json.loads(req.data.decode())
        self.assertEqual(payload["from"],
                         "Center for Belonging <hello@jemimahosei.com>")
        self.assertEqual(payload["to"], ["abc123@cornell.edu"])
        self.assertEqual(
            payload["subject"],
            "Confirm your subscription to the Center for Belonging newsletter")
        text = payload["text"]
        self.assertIn("Hi Test Person,", text)
        # The long URL goes out whole on one line — never folded.
        self.assertIn(CONFIRM_URL, text)
        self.assertTrue(all(ord(ch) < 128 for ch in text))
        self.assertEqual(mail.last_error(), "")

    def test_resend_from_bare_address_wrapped(self):
        os.environ["RESEND_API_KEY"] = "re_test_key_123"
        os.environ["RESEND_FROM"] = "news@jemimahosei.com"
        calls = self._capture_urlopen()
        mail.send_email("abc123@cornell.edu", "Issue 1", "Hello members",
                        "Center for Belonging",
                        "https://bowers-di-platform.onrender.com/newsletter")
        payload = json.loads(calls[0].data.decode())
        self.assertEqual(payload["from"],
                         "Center for Belonging <news@jemimahosei.com>")
        # Campaign footer: unsubscribe link included.
        self.assertIn(
            "https://bowers-di-platform.onrender.com/newsletter",
            payload["text"])
        self.assertIn("To stop receiving these emails", payload["text"])

    def test_no_sender_configured(self):
        """(b) Neither SMTP nor Resend: unconfigured, console mode."""
        self.assertFalse(mail.smtp_configured())
        self.assertFalse(mail.resend_configured())
        self.assertFalse(mail.email_configured())
        self.assertEqual(mail.email_mode(), "console")

    def test_resend_error_recorded_and_raised(self):
        """(c) A Resend HTTP error is recorded and raised to the caller."""
        os.environ["RESEND_API_KEY"] = "re_test_key_123"
        err = urllib.error.HTTPError(
            "https://api.resend.com/emails", 401, "Unauthorized", {},
            io.BytesIO(b'{"message": "Invalid API key"}'))
        with mock.patch.object(urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(urllib.error.HTTPError):
                mail.send_confirmation_email("abc123@cornell.edu", "",
                                             CONFIRM_URL)
        detail = mail.last_error()
        self.assertIn("401", detail)
        self.assertIn("Invalid API key", detail)
        # The key itself must never appear in the recorded error.
        self.assertNotIn("re_test_key_123", detail)

    def test_smtp_takes_priority_over_resend(self):
        """SMTP first when fully configured — Resend is never called."""
        os.environ["SMTP_HOST"] = "smtp.example.test"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USER"] = "user@example.test"
        os.environ["SMTP_PASS"] = "secret"
        os.environ["SMTP_FROM"] = "sender@example.test"
        os.environ["RESEND_API_KEY"] = "re_test_key_123"
        calls = self._capture_urlopen()
        with mock.patch.object(smtplib, "SMTP", _FakeSMTP):
            mail.send_confirmation_email("abc123@cornell.edu", "Test Person",
                                         CONFIRM_URL)
        self.assertEqual(calls, [])
        self.assertEqual(mail.email_mode(), "smtp")
        self.assertTrue(mail.email_configured())
        self.assertEqual(len(_FakeSMTP.instances), 1)
        sent = _FakeSMTP.instances[0].sent
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["From"],
                         "Center for Belonging <sender@example.test>")
        body = sent[0].get_content()
        self.assertIn(CONFIRM_URL, body)
        self.assertEqual(mail.last_error(), "")


if __name__ == "__main__":
    unittest.main()
