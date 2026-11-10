"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Conference } from "../lib/api";

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

export default function Home() {
  const [featured, setFeatured] = useState<Conference | null>(null);
  const [error, setError] = useState("");

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
  }, []);

  return (
    <>
      <div className="hero">
        <div className="hero-inner">
          <h1>You belong here.</h1>
          <p className="attribution">
            — Hakim Weatherspoon, Associate Dean for Belonging
          </p>
          <p>
            This is the Center for Belonging&apos;s tool to reach
            underrepresented students and get them using the Center&apos;s
            resources — at Cornell Bowers CIS.
          </p>
        </div>
      </div>
      <div className="container">
        {error && <p className="error">{error}</p>}
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
            <h3>Newsletter</h3>
            <p>
              Opt-in only. Get Center news and opportunities in your inbox.
            </p>
            <Link href="/newsletter">Sign up →</Link>
          </div>
          <div className="card">
            <h3>Book an appointment</h3>
            <p>
              Book an appointment or call with Dr. LeeAnn Roberts, Director
              of the DEIB office.
            </p>
            <Link href="/appointments">Request an appointment →</Link>
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
