"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  formatDateRange,
  type Conference,
  type Resource,
  type Slot,
} from "../lib/api";

/* Open Door home — mockups 01 (desktop) and 03 (phone; the same page
 * single-column via globals.css). Three sections: the hero with the
 * red door signup panel, the latest issue, and Talk to Dr. Roberts
 * pick-a-time booking. */

const TOPIC_CHIPS = [
  "Conferences and travel funding",
  "Scholarships and paid work",
  "Programs and events",
  "Support and resources",
];

const CORNELL_RE = /^[A-Za-z0-9._%+-]+@cornell\.edu$/i;

interface IssueRow {
  kind: string;
  title: string;
  note: string;
  when: string;
  /** Where a visitor goes to register/apply — every live row carries
   * one (Jemimah, 2026-11-22: the homepage listings must link out to
   * the real pages so people can act the same day). */
  link: string;
}

const BELONGING_LINK = "https://bowers.cornell.edu/belonging-bowers";
const HUB_LINK =
  "https://bowers.cornell.edu/belonging-bowers/resources-and-support";

/* Direct links for the homepage listings, taken from Cornell's own
 * pages (Jemimah, 2026-11-22: rows must link to the actual resource
 * or program page, not all to the Belonging homepage). Program links
 * are the "Learn more" destinations on bowers.cornell.edu/belonging-
 * bowers; resource links are the "Learn more" destinations on the
 * resources-and-support hub. Listings with no real page of their own
 * (Meta Days, Impact Week, GHC India) get no link rather than a
 * generic one. Keyed by the exact name/title in the platform data. */
const DIRECT_LINKS: Record<string, string> = {
  // Programs (events)
  "Two-year career program": "https://bowers.cornell.edu/belonging-bowers/ascend",
  CSMore: "https://bowers.cornell.edu/belonging-bowers/csmore",
  "Belonging at Bowers Awards": "https://bowers.cornell.edu/excellence-awards/belonging-awards",
  "Dinner with the Deans+": "https://bowers.cornell.edu/belonging-bowers/dinner-deans",
  EngageLEAP: "https://bowers.cornell.edu/belonging-bowers/engage-leap",
  "Weeklong immersive research workshop": "https://bowers.cornell.edu/node/7419",
  "Alumni mentorship small groups":
    "https://bowers.cornell.edu/news-stories/bowers-alumni-roundtable-yields-helpful-advice-undergrads",
  // Community resources
  "Anti-racism, antisemitism, and Islamophobia resources":
    "https://diversity.cornell.edu/community-resources/diversity-and-inclusion-resources",
  "Mental health and wellbeing": "https://mentalhealth.cornell.edu/",
  "Bias reporting": "https://diversity.cornell.edu/initiatives-programs/bias-reporting-cornell",
  "Accessibility and disability resources":
    "https://diversity.cornell.edu/initiatives-programs/disability-access",
  "OIETIX (Title IX)": "https://titleix.cornell.edu/",
  "LGBTQ+ resources":
    "https://diversity.cornell.edu/our-community/staff-resources/lgbtq-staff-faculty/transgender-inclusion-cornell",
  OADI: "https://oadi.cornell.edu/",
  "Belonging & Support Services (Student & Campus Life)":
    "https://scl.cornell.edu/belonging-support-services",
  "Student Disability Services": "https://sds.cornell.edu",
  "Future Faculty teaching and mentoring": "https://futurefaculty.cornell.edu/",
  "OISE (graduate development)": "https://gradschool.cornell.edu/diversity-inclusion/about-oise/",
  "Office of Postdoctoral Studies": "https://postdocs.cornell.edu/",
  "International Services (Office of Global Learning)":
    "https://international.globallearning.cornell.edu/",
  "Colleague Network Groups (HR employee resource groups)":
    "https://hr.cornell.edu/culture/community/colleague-network-groups",
  "Department of Inclusion and Belonging (HR)":
    "https://hr.cornell.edu/culture/inclusion-and-belonging",
  "Inclusive Excellence Network (staff)":
    "https://hr.cornell.edu/culture/inclusion-belonging/learning-and-development",
  "OFDD (faculty development and diversity)": "https://facultydevelopment.cornell.edu/",
  "CTI inclusive-teaching course":
    "https://teaching.cornell.edu/programs/faculty-instructors/faculty-institutes",
  "CTL (startups and commercialization)": "https://ctl.cornell.edu/",
  "Diversity Alumni Programs and Cornell Mosaic": "https://alumni.cornell.edu/connect/diversity/",
};

/* The mockup's example rows, shown when the API has nothing live yet
 * (the mockup itself labels its rows as examples for staff to fill). */
const EXAMPLE_ROWS: IssueRow[] = [
  {
    kind: "Conference funding",
    title: "Tapia Conference travel support",
    note: "Funding covers registration and travel. Short form, no essay.",
    when: "Apply by Jan 20",
    link: BELONGING_LINK,
  },
  {
    kind: "Conference funding",
    title: "Grace Hopper Celebration",
    note: "Request support, and join the Center's group for the trip.",
    when: "Apply by Feb 3",
    link: BELONGING_LINK,
  },
  {
    kind: "Program",
    title: "CSMore",
    note: "Computer science support for students from other majors.",
    when: "Opens Feb 10",
    link: BELONGING_LINK,
  },
  {
    kind: "Event",
    title: "Dinner with the Deans+",
    note: "Small tables, real conversation, free food.",
    when: "Feb 18, 6 PM",
    link: BELONGING_LINK,
  },
];

function slotLabel(slot: Slot): string {
  const d = new Date(`${slot.date}T12:00:00`);
  const day = d.toLocaleDateString("en-US", { weekday: "short" });
  const [h, m] = slot.start_time.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const time = m ? `${h12}:${String(m).padStart(2, "0")} ${ampm}` : `${h12} ${ampm}`;
  return `${day} ${time}`;
}

type SignupMode = "form" | "inbox" | "done" | "fail";

export default function Home() {
  /* ------------------------------ signup ------------------------------ */
  const [mode, setMode] = useState<SignupMode>("form");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  const [picks, setPicks] = useState<boolean[]>(TOPIC_CHIPS.map(() => true));
  const [sending, setSending] = useState(false);

  /* --------------------------- latest issue --------------------------- */
  const [issueRows, setIssueRows] = useState<IssueRow[]>(EXAMPLE_ROWS);
  const [issueIsExample, setIssueIsExample] = useState(true);

  /* ------------------------------ booking ----------------------------- */
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [slotIdx, setSlotIdx] = useState(0);
  const [bName, setBName] = useState("");
  const [bEmail, setBEmail] = useState("");
  const [bPurpose, setBPurpose] = useState("");
  const [bErr, setBErr] = useState("");
  const [booked, setBooked] = useState(false);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    Promise.allSettled([api.resources(), api.conferences(), api.events()])
      .then(([resR, confR, evR]) => {
        const rows: IssueRow[] = [];
        if (confR.status === "fulfilled") {
          confR.value
            .filter((c: Conference) => c.status === "upcoming")
            .forEach((c: Conference) =>
              rows.push({
                kind: "Conference",
                title: c.name,
                note: c.description ?? "",
                when: formatDateRange(c.date, c.end_date),
                link: c.link || DIRECT_LINKS[c.name] || "",
              })
            );
        }
        if (evR.status === "fulfilled") {
          evR.value.forEach((e) =>
            rows.push({
              kind: e.category
                ? e.category.charAt(0).toUpperCase() + e.category.slice(1)
                : "Event",
              title: e.name,
              note: e.description ?? "",
              when: e.date ?? "",
              link: DIRECT_LINKS[e.name] || "",
            })
          );
        }
        if (resR.status === "fulfilled") {
          resR.value.forEach((r: Resource) =>
            rows.push({
              kind: r.category,
              title: r.title,
              note: r.description,
              when: "",
              link: DIRECT_LINKS[r.title] || r.link || HUB_LINK,
            })
          );
        }
        if (rows.length > 0) {
          setIssueRows(rows.slice(0, 8));
          setIssueIsExample(false);
        }
      })
      .catch(() => {
        /* keep the example rows */
      });
    api
      .slots(true)
      .then(setSlots)
      .catch(() => setSlots([]));
  }, []);

  async function submitSignup(e: React.FormEvent) {
    e.preventDefault();
    const em = email.trim();
    if (!CORNELL_RE.test(em)) {
      setErr(em ? "Use your @cornell.edu address." : "Enter your Cornell email.");
      return;
    }
    setErr("");
    setSending(true);
    try {
      const res = await api.newsletterSignup({
        name: name.trim(),
        email: em,
        interests: [],
        topics: TOPIC_CHIPS.filter((_, i) => picks[i]),
        source: "website",
      });
      if (res.already_subscribed) {
        setMode("done");
      } else if (res.email_sent) {
        // The confirmation email is the channel — never show the link
        // on the page (Jemimah's settled rule).
        setMode("inbox");
      } else {
        // No confirmation email went out. Preserve the existing
        // /newsletter fallback: hand the token over via sessionStorage
        // so that page can confirm, and show the mockup's fail state.
        if (res.confirmation_token) {
          try {
            window.sessionStorage.setItem(
              "bowers-pending-confirmation",
              JSON.stringify({
                already: res.already_subscribed,
                email_sent: res.email_sent,
                email_configured: res.email_configured,
                token: res.confirmation_token,
                url: res.confirmation_url,
                email: em,
              })
            );
          } catch {
            /* storage unavailable — /newsletter signup issues a fresh token */
          }
        }
        setMode("fail");
      }
    } catch {
      setMode("fail");
    } finally {
      setSending(false);
    }
  }

  function resetSignup() {
    setMode("form");
    setEmail("");
    setErr("");
  }

  async function submitBooking(e: React.FormEvent) {
    e.preventDefault();
    const slot = slots?.[slotIdx];
    if (!slot) return;
    if (!bName.trim()) {
      setBErr("Enter your name so Dr. Roberts knows who is coming.");
      return;
    }
    if (!CORNELL_RE.test(bEmail.trim())) {
      setBErr("Use your @cornell.edu address so Dr. Roberts can reply.");
      return;
    }
    setBErr("");
    setBooking(true);
    try {
      await api.bookSlot(slot.id, {
        name: bName.trim(),
        email: bEmail.trim(),
        purpose: bPurpose.trim(),
      });
      setBooked(true);
      setSlots((prev) => (prev ? prev.filter((s) => s.id !== slot.id) : prev));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("409")) {
        setBErr("That time was just taken. Pick another one.");
        api
          .slots(true)
          .then(setSlots)
          .catch(() => undefined);
      } else if (msg.includes("400")) {
        setBErr("A Cornell email address is required to book.");
      } else {
        setBErr("Could not book that time. Try again.");
      }
    } finally {
      setBooking(false);
    }
  }

  const pickedSlot = slots?.[slotIdx] ?? null;

  return (
    <>
      {/* ------------------------------ Hero ------------------------------ */}
      <section className="od-hero">
        <div>
          <h1>Opportunities for Bowers students, sent to you.</h1>
          <p className="od-sub">
            Open Door is the newsletter from the Center for Belonging at
            Cornell Bowers CIS. Each issue lists the conferences, funding,
            programs and support open to you right now, with the deadline
            next to each one.
          </p>
          <p className="od-official">
            Looking for something else about the college? The official site
            is{" "}
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

        <div className="od-door">
          <div className="od-door-panel">
            {mode === "form" && (
              <form onSubmit={submitSignup} noValidate>
                <h2>Get the next issue</h2>
                <div className="od-door-field">
                  <label htmlFor="od-name">Name, if you like</label>
                  <input
                    id="od-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                  />
                </div>
                <div className="od-door-field">
                  <label htmlFor="od-email">Cornell email</label>
                  <input
                    id="od-email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setErr("");
                    }}
                    placeholder="netid@cornell.edu"
                    autoComplete="email"
                    aria-describedby="od-email-help"
                  />
                  <div id="od-email-help" className="od-door-error" aria-live="polite">
                    {err && <span>{err}</span>}
                  </div>
                </div>
                <fieldset>
                  <legend>What should we send you?</legend>
                  <div className="od-chips">
                    {TOPIC_CHIPS.map((chip, i) => (
                      <button
                        key={chip}
                        type="button"
                        className="od-chip"
                        aria-pressed={picks[i]}
                        onClick={() =>
                          setPicks((prev) =>
                            prev.map((p, j) => (j === i ? !p : p))
                          )
                        }
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <button
                  type="submit"
                  className="od-door-submit"
                  disabled={sending}
                >
                  {sending ? "Subscribing…" : "Subscribe"}
                </button>
                <p className="od-door-fine">
                  We email a confirmation link first. Every issue has
                  one-click unsubscribe.
                </p>
              </form>
            )}

            {mode === "inbox" && (
              <div aria-live="polite">
                <h2>Check your inbox</h2>
                <p className="od-door-body">
                  We sent a confirmation link to{" "}
                  <strong>{email.trim() || "netid@cornell.edu"}</strong>.
                  Open it and you are on the list.
                </p>
                <p className="od-door-sub">
                  Nothing arrived after a few minutes? Check spam, or start
                  again with the same address.
                </p>
                <button
                  type="button"
                  className="od-door-soft"
                  onClick={resetSignup}
                >
                  Use a different address
                </button>
              </div>
            )}

            {mode === "done" && (
              <div aria-live="polite">
                <h2>You are on the list</h2>
                <p className="od-door-body">
                  Your address is confirmed. The next issue lands in your
                  inbox, and the latest one is just below.
                </p>
                <a className="od-door-link" href="#issue">
                  Read the latest issue
                </a>
              </div>
            )}

            {mode === "fail" && (
              <div aria-live="polite">
                <h2>We could not send it</h2>
                <p className="od-door-body">
                  The confirmation email did not go out, so you are not
                  subscribed yet. Nothing was lost on your side.
                </p>
                <button
                  type="button"
                  className="od-door-submit"
                  onClick={resetSignup}
                >
                  Try again
                </button>
                <p className="od-door-fine">
                  Still stuck? Email deib-office@bowers.cornell.edu and we
                  will add you by hand.{" "}
                  <Link href="/newsletter" style={{ color: "#fff" }}>
                    Or confirm on the newsletter page
                  </Link>
                  .
                </p>
              </div>
            )}
          </div>
          <div className="od-door-step" aria-hidden="true" />
        </div>
      </section>

      {/* -------------------------- Latest issue -------------------------- */}
      <section id="issue" className="od-section">
        <div className="od-issue-grid">
          <div className="od-issue-side">
            <h2>The latest issue</h2>
            <p>
              What lands in your inbox, shown here as a web page too.
              {issueIsExample
                ? " The titles and dates below are examples. Staff fill in the real ones before each send."
                : " These are the Center's live listings, the same ones staff build each issue from."}
            </p>
            <h3>How it works</h3>
            <ol>
              <li>Subscribe with your Cornell email.</li>
              <li>Open the confirmation link we send you.</li>
              <li>
                Each issue arrives with deadlines and links, so you can
                apply the same day.
              </li>
            </ol>
          </div>
          <article className="od-issue-article">
            <div className="od-issue-eyebrow">
              {issueIsExample ? "Example issue" : "Latest listings"}
            </div>
            <h3>
              {issueIsExample
                ? "Funding is open for two conferences"
                : "What is open right now"}
            </h3>
            <p>
              Here is what to apply for, and by when. Replies go to
              Dr. Roberts, who reads every one.
            </p>
            <div className="od-issue-rows">
              {issueRows.map((o, i) => (
                <div className="od-issue-row" key={`${o.title}-${i}`}>
                  <div className="main">
                    <div className="kind">{o.kind}</div>
                    <div className="title">{o.title}</div>
                    {o.note && <div className="note">{o.note}</div>}
                    {o.link && (
                      <a
                        className="od-issue-apply"
                        href={o.link}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Apply or register →
                      </a>
                    )}
                  </div>
                  {o.when && (
                    <div className="when">
                      <strong>{o.when}</strong>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="od-issue-foot">
              You are getting this because you subscribed with your Cornell
              email. Unsubscribe in one click.
            </p>
          </article>
        </div>
      </section>

      {/* ----------------------------- Booking ---------------------------- */}
      <section id="talk" className="od-section">
        <div className="od-talk-card">
          <div className="od-talk-intro">
            <h2>Talk to Dr. Roberts</h2>
            <p>
              LeeAnn Roberts directs the DEIB office. Pick a time to talk
              about funding, a program, or anything on your mind. By call
              or in person.
            </p>
          </div>
          <div className="od-talk-form">
            {booked && pickedSlot ? (
              <div className="od-booked" aria-live="polite">
                <h3>Booked, {slotLabel(pickedSlot)}</h3>
                <p>
                  A confirmation is on its way to {bEmail.trim()}. That
                  time is now held for you.
                </p>
                <button
                  type="button"
                  className="od-slot"
                  style={{ marginTop: 16 }}
                  onClick={() => {
                    setBooked(false);
                    setBEmail("");
                    setSlotIdx(0);
                  }}
                >
                  Book another time
                </button>
              </div>
            ) : slots === null ? (
              <p>Loading open times…</p>
            ) : slots.length === 0 ? (
              <p>
                No open times right now. Email{" "}
                <a href="mailto:deib-office@bowers.cornell.edu">
                  deib-office@bowers.cornell.edu
                </a>{" "}
                instead, and Dr. Roberts will find a time with you.
              </p>
            ) : (
              <form onSubmit={submitBooking} noValidate>
                <div className="od-slot-label" id="od-slot-label">
                  Open times
                </div>
                <div
                  className="od-slots"
                  role="group"
                  aria-labelledby="od-slot-label"
                >
                  {slots.map((s, i) => (
                    <button
                      key={s.id}
                      type="button"
                      className="od-slot"
                      aria-pressed={slotIdx === i}
                      onClick={() => setSlotIdx(i)}
                    >
                      {slotLabel(s)} · {s.type === "call" ? "Call" : "In person"}
                    </button>
                  ))}
                </div>
                <label htmlFor="od-bname">Your name</label>
                <input
                  id="od-bname"
                  type="text"
                  value={bName}
                  onChange={(e) => setBName(e.target.value)}
                  autoComplete="name"
                />
                <label htmlFor="od-bemail">Your Cornell email</label>
                <input
                  id="od-bemail"
                  type="email"
                  value={bEmail}
                  onChange={(e) => {
                    setBEmail(e.target.value);
                    setBErr("");
                  }}
                  placeholder="netid@cornell.edu"
                  autoComplete="email"
                />
                <label htmlFor="od-bpurpose">
                  What would you like to talk about? (optional)
                </label>
                <input
                  id="od-bpurpose"
                  type="text"
                  value={bPurpose}
                  onChange={(e) => setBPurpose(e.target.value)}
                  placeholder="e.g. conference support, resources, advising"
                />
                <div className="od-form-error" aria-live="polite">
                  {bErr}
                </div>
                <button
                  type="submit"
                  className="od-book-btn"
                  disabled={booking}
                >
                  {booking ? "Booking…" : "Book this time"}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
