"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { DoorMark } from "../../components/Header";

/* Unsubscribe — mockup 05 ("Unsubscribe link from an issue").
 *
 * Route finding (see APPLY_NOTES.md): there is NO dedicated
 * unsubscribe route or token in the current app. Campaign emails are
 * sent with the unsubscribe link pointing at {FRONTEND_URL}/newsletter
 * (backend send_campaign: unsubscribe_url = f"{base}/newsletter"),
 * and unsubscribing itself is POST /api/newsletter/unsubscribe
 * {email} — api.newsletterUnsubscribe. This page is that flow in the
 * mockup's shape: it reads ?email= from the URL (the staged optional
 * backend patch makes issue emails link here with the recipient's
 * address filled in); with no ?email= it asks for the address, so it
 * also works when reached from /newsletter or typed directly.
 * The global header is suppressed on this route. */

type Phase = "ask" | "working" | "done";

export default function UnsubscribePage() {
  const [email, setEmail] = useState("");
  const [emailFromLink, setEmailFromLink] = useState(false);
  const [phase, setPhase] = useState<Phase>("ask");
  const [error, setError] = useState("");

  useEffect(() => {
    const fromQuery = new URLSearchParams(window.location.search).get("email");
    if (fromQuery) {
      setEmail(fromQuery);
      setEmailFromLink(true);
    }
  }, []);

  async function stop(e?: React.FormEvent) {
    if (e) e.preventDefault();
    const em = email.trim().toLowerCase();
    if (!em || !em.includes("@")) {
      setError("Enter the email address the issues are sent to.");
      return;
    }
    setError("");
    setPhase("working");
    try {
      await api.newsletterUnsubscribe(em);
      setPhase("done");
    } catch {
      setPhase("ask");
      setError("Unsubscribe failed. Check the email and try again.");
    }
  }

  return (
    <div className="od-auth-wrap">
      <div className="od-auth-col">
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            minHeight: 44,
            textDecoration: "none",
            fontWeight: 700,
            fontSize: 20,
            lineHeight: 1.1,
            color: "var(--text)",
          }}
        >
          <DoorMark size={20} />
          Open Door
        </Link>

        {phase !== "done" ? (
          <div>
            <h1>Stop the emails?</h1>
            {emailFromLink ? (
              <p className="od-auth-sub">
                This removes <strong>{email}</strong> from Open Door. It
                takes effect now, and you can subscribe again any time.
              </p>
            ) : (
              <>
                <p className="od-auth-sub">
                  This removes your address from Open Door. It takes
                  effect now, and you can subscribe again any time.
                </p>
                <form onSubmit={stop} noValidate>
                  <label htmlFor="od-unsub-email">Cornell email</label>
                  <input
                    id="od-unsub-email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setError("");
                    }}
                    placeholder="netid@cornell.edu"
                    autoComplete="email"
                  />
                </form>
              </>
            )}
            <div className="od-auth-error" aria-live="polite">
              {error}
            </div>
            <button
              type="button"
              className="od-auth-submit"
              style={{ marginTop: 22 }}
              onClick={() => stop()}
              disabled={phase === "working"}
            >
              {phase === "working" ? "Unsubscribing…" : "Unsubscribe"}
            </button>
            <Link href="/" className="od-auth-outline">
              Keep me subscribed
            </Link>
          </div>
        ) : (
          <div aria-live="polite">
            <h1>You are unsubscribed</h1>
            <p className="od-auth-sub">
              No more issues will be sent to {email.trim().toLowerCase()}.
              Clicked by mistake?
            </p>
            <Link
              href="/"
              className="od-auth-submit"
              style={{
                marginTop: 22,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                textDecoration: "none",
                background: "var(--accent)",
                color: "#fff",
                borderRadius: 6,
                fontWeight: 700,
              }}
            >
              Subscribe again
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
