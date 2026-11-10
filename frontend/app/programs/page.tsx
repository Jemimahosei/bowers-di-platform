"use client";

import { useEffect, useState } from "react";
import { api, formatDateRange, type CenterEvent } from "../../lib/api";

/* Center programs verified from the Belonging at Bowers pages and from
 * jem (REAL-SPEC.md §7.1–7.2). The venue for the alumni dinner is
 * recorded exactly as jem said it: "the Baytech building". */
const KNOWN_PROGRAMS: {
  name: string;
  description: string;
  category: string;
}[] = [
  {
    name: "CSMore",
    description:
      "Summer program for rising sophomores (Jul 15–Aug 9), run by the DEIB office in Gates Hall; funded by the CS department, NSF, LinkedIn, and the Hopper-Dean Foundation.",
    category: "program",
  },
  {
    name: "Belonging at Bowers Awards",
    description:
      "Annual awards celebrating faculty, staff, students, alumni, and community leaders.",
    category: "program",
  },
  {
    name: "Dinner with the Deans+",
    description:
      "Undergrads, professionals, and doctoral students with college leadership.",
    category: "community",
  },
  {
    name: "EngageLEAP",
    description: "Program for doctoral scholars in computing.",
    category: "program",
  },
  {
    name: "Meta Days",
    description:
      "Meta came to campus with a bunch of employees for a couple of days: talks in classes, coffee chats, dinners, and panels between students and Meta employees.",
    category: "program",
  },
  {
    name: "Cornell alumni dinner",
    description:
      "Dinner with alumni from startups and big tech, at the Baytech building.",
    category: "community",
  },
  {
    name: "Weeklong immersive research workshop",
    description:
      "A weeklong immersive research workshop inspiring underrepresented students toward graduate study.",
    category: "workshop",
  },
  {
    name: "Two-year career program",
    description:
      "A two-year program advancing students' careers in tech: research, entrepreneurship, and experiential learning.",
    category: "program",
  },
  {
    name: "Alumni mentorship small groups",
    description: "Alumni connections and mentorship in small groups.",
    category: "community",
  },
  {
    name: "Impact Week (B@C 360)",
    description:
      "College-wide belonging week, Sep 28–Oct 4; committee lead Dr. LeeAnn Roberts.",
    category: "program",
  },
];

export default function ProgramsPage() {
  const [events, setEvents] = useState<CenterEvent[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .events()
      .then(setEvents)
      .catch(() =>
        setError("Could not reach the API. Is the backend running?")
      );
  }, []);

  // Show API events first; the verified program list below is the
  // Center's standing programs (also served by the API when seeded).
  const apiNames = new Set(events.map((e) => e.name.toLowerCase()));
  const extra = KNOWN_PROGRAMS.filter(
    (p) => !apiNames.has(p.name.toLowerCase())
  );

  return (
    <div className="container">
      <h1>Programs</h1>
      <p className="lede">
        Center for Belonging programs and events — from the Center&apos;s own
        Belonging at Bowers pages and the Center&apos;s work.
      </p>
      {error && <p className="error">{error}</p>}

      {events.length > 0 && (
        <>
          <h2>Center events</h2>
          <div className="grid">
            {events.map((e) => (
              <article className="card" key={e.id}>
                <h3>{e.name}</h3>
                {e.date && <p>{formatDateRange(e.date, null)}</p>}
                {e.description && <p>{e.description}</p>}
                <div className="tags">
                  <span className="tag">{e.category}</span>
                  {e.location && (
                    <span className="tag neutral">{e.location}</span>
                  )}
                  {e.status && (
                    <span className="tag neutral">{e.status}</span>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      <h2>Center programs</h2>
      <div className="grid">
        {extra.map((p) => (
          <article className="card" key={p.name}>
            <h3>{p.name}</h3>
            <p>{p.description}</p>
            <div className="tags">
              <span className="tag">{p.category}</span>
            </div>
          </article>
        ))}
      </div>
      {extra.length === 0 && events.length === 0 && !error && (
        <p>No programs listed yet.</p>
      )}
      <p className="lede">
        Questions about a program? Email{" "}
        <a href="mailto:deib-office@bowers.cornell.edu">
          deib-office@bowers.cornell.edu
        </a>
        .
      </p>
    </div>
  );
}
