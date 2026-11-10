"use client";

import { useEffect, useState } from "react";
import { api, formatDateRange, type Conference } from "../../lib/api";

function ConferenceCard({ c }: { c: Conference }) {
  return (
    <article className={`card${c.status === "cancelled" ? " cancelled" : ""}`}>
      <h3>{c.name}</h3>
      <p>
        {formatDateRange(c.date, c.end_date)}
        {c.location ? ` · ${c.location}` : ""}
      </p>
      {c.description && <p>{c.description}</p>}
      <div className="tags">
        <span className={`tag${c.status === "cancelled" ? " warn" : ""}`}>
          {c.status === "tba"
            ? "Details to be announced"
            : c.status === "upcoming"
              ? "Upcoming"
              : c.status === "past"
                ? "Past"
                : "Cancelled"}
        </span>
        {c.attendees != null && (
          <span className="tag neutral">{c.attendees} attendees</span>
        )}
      </div>
      {c.link && (
        <p>
          <a href={c.link} target="_blank" rel="noopener">
            Learn more →
          </a>
        </p>
      )}
    </article>
  );
}

export default function ConferencesPage() {
  const [items, setItems] = useState<Conference[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .conferences()
      .then(setItems)
      .catch(() =>
        setError("Could not reach the API. Is the backend running?")
      );
  }, []);

  const upcoming = items.filter(
    (c) => c.status === "upcoming" || c.status === "tba"
  );
  const past = items.filter((c) => c.status === "past");
  const cancelled = items.filter((c) => c.status === "cancelled");

  return (
    <div className="container">
      <h1>Conferences</h1>
      <p className="lede">
        The Center for Belonging&apos;s flagship conferences: Grace Hopper,
        Tapia, and Code Afrique.
      </p>
      {error && <p className="error">{error}</p>}

      <h2>Upcoming</h2>
      <div className="grid">
        {upcoming.map((c) => (
          <ConferenceCard key={c.id} c={c} />
        ))}
      </div>
      {!error && upcoming.length === 0 && (
        <p>No upcoming conferences listed yet.</p>
      )}

      <h2>Past</h2>
      <div className="grid">
        {past.map((c) => (
          <ConferenceCard key={c.id} c={c} />
        ))}
      </div>
      {!error && past.length === 0 && (
        <p>No past conferences listed yet.</p>
      )}

      <h2>Cancelled</h2>
      <div className="grid">
        {cancelled.map((c) => (
          <ConferenceCard key={c.id} c={c} />
        ))}
      </div>
      {!error && cancelled.length === 0 && (
        <div className="card cancelled">
          <h3>Grace Hopper Celebration 2026 — Cancelled</h3>
          <p>
            AnitaB.org cancelled Grace Hopper Celebration 2026 on Oct 13,
            2026, about two weeks before its Oct 27–30 dates in Anaheim,
            because of funding shortfalls. It is not an upcoming conference.
            GHC India is still on: Jan 20–22, 2027, Bangalore.
          </p>
        </div>
      )}
      {cancelled.length > 0 && (
        <p className="lede">
          Grace Hopper Celebration 2026 was cancelled by AnitaB.org on Oct
          13, 2026 — it is never presented as upcoming. GHC India is still
          on: Jan 20–22, 2027, Bangalore.
        </p>
      )}
    </div>
  );
}
