"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Conference, type Slot } from "../lib/api";

/* Program impact numbers from the Center's own reporting
 * (REAL-SPEC.md §1.4 / §6 item 8): labelled as program impact numbers. */
const IMPACT_STATS = [
  { value: "100+", label: "Students served", note: "across the flagship initiatives" },
  { value: "3", label: "Flagship initiatives", note: "Grace Hopper, Tapia, Code Afrique" },
  { value: "2", label: "Departments", note: "Computer Science & Information Science" },
  { value: "100+", label: "Stakeholders", note: "faculty, students, staff" },
  { value: "40%", label: "Increase in resource utilization", note: "through redesign of physical and operational workflows" },
  { value: "$4,000", label: "Program budget", note: "program impact number" },
];

function isCornellEmail(email: string): boolean {
  return email.trim().toLowerCase().endsWith("@cornell.edu");
}

export default function Home() {
  const [featured, setFeatured] = useState<Conference | null>(null);
  const [openSlots, setOpenSlots] = useState<Slot[] | null>(null);
  const [error, setError] = useState("");
  const [subEmail, setSubEmail] = useState("");
  const [subError, setSubError] = useState("");
  const [subResult, setSubResult] = useState<{
    already?: boolean;
    email_sent?: boolean;
    smtp_configured?: boolean;
    token?: string;
    url?: string;
    email?: string;
  } | null>(null);

  useEffect(() => {
    api
      .conferences()
      .then((list) => {
        const upcoming = list.filter((c) => c.status === "upcoming");
        const ghc = upcoming.find((c) => c.name.includes("GHC India"));
        setFeatured(ghc ?? upcoming[0] ?? null);
      })
      .catch(() =>
        setError("Could not reach the API — conference data is unavailable right now.")
      );
    api
      .slots(true)
      .then(setOpenSlots)
      .catch(() => setOpenSlots([]));
  }, []);

  async function submitSubscribe(e: React.FormEvent) {
    e.preventDefault();
    setSubError("");
    setSubResult(null);
    if (!isCornellEmail(subEmail)) {
      setSubError("Use your Cornell email to subscribe.");
      return;
    }
    try {
      const res = await api.newsletterSignup({
        name: "",
        email: subEmail,
        interests: [],
        topics: [],
        source: "website",
      });
      const result = {
        already: res.already_subscribed,
        email_sent: res.email_sent,
        smtp_configured: res.smtp_configured,
        token: res.confirmation_token,
        url: res.confirmation_url,
        email: subEmail,
      };
      setSubResult(result);
      // No link is ever shown on the homepage. When the confirmation
      // email did not go out, the confirmation step lives on
      // /newsletter — hand the token over via sessionStorage so that
      // page can show the fallback link.
      if (!result.already && !result.email_sent && result.token) {
        try {
          window.sessionStorage.setItem(
            "bowers-pending-confirmation",
            JSON.stringify(result)
          );
        } catch {
          // Storage unavailable — signing up again on /newsletter
          // issues a fresh token, so the step still works.
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setSubError(
        msg.includes("Cornell")
          ? "Use your Cornell email to subscribe."
          : "Could not sign up. Check the API and try again."
      );
    }
  }

  return (
    <>
      <div className="hero">
        <div className="hero-inner">
          <h1>
            Welcome — the Center&apos;s resources and opportunities, in
            your inbox.
          </h1>
          <p className="attribution">
            “You belong here.” — Hakim Weatherspoon, Associate Dean for
            Belonging
          </p>
          <p>
            You&apos;re in the right place. Sign up once with your
            Cornell email, and every issue brings you a steady supply of
            what the Center has for you — real resources, plus
            opportunities: conference funding and deadlines, scholarships
            and paid opportunities, events and programs. It keeps coming,
            so you don&apos;t have to go looking for it.
          </p>
          {subError && <p className="hero-error">{subError}</p>}
          {subResult?.email_sent ? (
            <p className="hero-note">
              Check your inbox — we sent a confirmation email to{" "}
              {subResult.email}. If you don&apos;t see it, check your
              spam folder.
            </p>
          ) : subResult?.already ? (
            <p className="hero-note">
              You&apos;re already subscribed — the next issue is on its
              way to your Cornell inbox.
            </p>
          ) : subResult ? (
            <p className="hero-note">
              You&apos;re almost in —{" "}
              <Link href="/newsletter">
                head to the newsletter page to confirm your subscription
              </Link>
              .
            </p>
          ) : (
            <form className="hero-signup" onSubmit={submitSubscribe}>
              <input
                type="email"
                required
                value={subEmail}
                onChange={(e) => setSubEmail(e.target.value)}
                placeholder="netid@cornell.edu"
                aria-label="Cornell email"
              />
              <button type="submit">Sign up</button>
              <span className="fine">
                Cornell email only — use your @cornell.edu address.
              </span>
            </form>
          )}
        </div>
      </div>
      <div className="container">
        {error && <p className="error">{error}</p>}

        <h2>What you&apos;ll get, every issue</h2>
        <p className="lede">
          Sign up once and it keeps coming — every issue brings you a
          fresh supply of what the Center has for you.
        </p>
        <div className="grid">
          <div className="card">
            <h3>Real resources</h3>
            <p>
              The Center&apos;s office services, community resources, and
              campus partners — picked for that issue, with links so you
              can use them right away.
            </p>
          </div>
          <div className="card">
            <h3>Opportunities</h3>
            <p>
              Conference funding and deadlines (Grace Hopper, Tapia,
              Code Afrique), scholarships and paid opportunities — what
              to apply for, and by when.
            </p>
          </div>
          <div className="card">
            <h3>Events and programs</h3>
            <p>
              What the Center is running — and how to take part.
            </p>
          </div>
        </div>

        <h2>How the Center reaches you</h2>
        <div className="grid">
          <div className="card">
            <h3>The newsletter — the core</h3>
            <p>
              Each issue sends the Center&apos;s resources to students at
              the Cornell domain — resources, conference funding and
              deadlines, events. Sign up with your Cornell email and it
              comes to you.
            </p>
            <p>
              <Link href="/newsletter">Subscribe →</Link>
              {" · "}
              <Link href="/campaigns">Staff: compose an issue →</Link>
            </p>
          </div>
          <div className="card">
            <h3>Audiences — who to reach</h3>
            <p>
              Student organizations share their lists with the Center&apos;s
              agreement, and the platform takes them in — by CSV upload,
              manual add, or an org representative&apos;s submission. No
              roster is ever taken without permission.
            </p>
            <p>
              <Link href="/audiences">Manage audiences →</Link>
              {" · "}
              <Link href="/org-submit">Submit your org&apos;s contacts →</Link>
            </p>
          </div>
          <div className="card">
            <h3>Book an appointment — talk to us</h3>
            <p>
              Real open times with Dr. LeeAnn Roberts, Director of the DEIB
              office. Pick a slot, book it, and it&apos;s yours — by call or
              in person.
            </p>
            <p>
              <Link href="/appointments">Book an appointment →</Link>
            </p>
            {openSlots !== null && (
              <p>
                {openSlots.length === 0
                  ? "No open times right now — Dr. Roberts adds availability here."
                  : `${openSlots.length} open time${openSlots.length === 1 ? "" : "s"} available.`}
              </p>
            )}
          </div>
        </div>

        <h2>Program impact</h2>
        <div className="stats">
          {IMPACT_STATS.map((s) => (
            <div className="stat" key={s.label}>
              <strong>{s.value}</strong>
              <span>{s.label}</span>
              <span className="note">{s.note}</span>
            </div>
          ))}
        </div>

        <h2>Featured upcoming conference</h2>
        <div className="card">
          <h3>
            {featured ? (
              <Link href="/conferences">{featured.name}</Link>
            ) : (
              "GHC India, Jan 20–22, 2027"
            )}
          </h3>
          <p>
            {featured?.description ??
              "Grace Hopper Celebration India — Jan 20–22, 2027, Bangalore."}
          </p>
          <p>
            <Link href="/conferences">See all conferences →</Link>
          </p>
        </div>

        <h2>Find what you need</h2>
        <div className="grid">
          <div className="card">
            <h3>Resources</h3>
            <p>
              Office services, community resources, and campus partners —
              search and filter for your situation.
            </p>
            <Link href="/resources">Browse resources →</Link>
          </div>
          <div className="card">
            <h3>Conferences</h3>
            <p>
              Grace Hopper, Tapia, and Code Afrique — upcoming, past, and
              cancelled.
            </p>
            <Link href="/conferences">View conferences →</Link>
          </div>
          <div className="card">
            <h3>Programs</h3>
            <p>
              CSMore, Belonging at Bowers Awards, Dinner with the Deans+,
              EngageLEAP, Meta Days, and more.
            </p>
            <Link href="/programs">View programs →</Link>
          </div>
          <div className="card">
            <h3>Book an appointment</h3>
            <p>
              Real open times with Dr. LeeAnn Roberts, Director of the DEIB
              office — by call or in person.
            </p>
            <Link href="/appointments">Book an appointment →</Link>
          </div>
        </div>

        <h2>Contact the Center</h2>
        <p>
          Email{" "}
          <a href="mailto:deib-office@bowers.cornell.edu">
            deib-office@bowers.cornell.edu
          </a>{" "}
          or visit{" "}
          <a
            href="https://diversity.cis.cornell.edu"
            target="_blank"
            rel="noopener"
          >
            diversity.cis.cornell.edu
          </a>
          .
        </p>
      </div>
    </>
  );
}
