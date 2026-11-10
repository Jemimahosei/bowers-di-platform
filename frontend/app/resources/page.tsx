"use client";

import { useEffect, useMemo, useState } from "react";
import {
  api,
  RESOURCE_CATEGORIES,
  type Resource,
} from "../../lib/api";

export default function ResourcesPage() {
  const [items, setItems] = useState<Resource[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [audience, setAudience] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .resources({
          search: search || undefined,
          category: category || undefined,
          audience: audience || undefined,
        })
        .then(setItems)
        .catch(() =>
          setError("Could not reach the API. Is the backend running?")
        );
    }, 250);
    return () => clearTimeout(timer);
  }, [search, category, audience]);

  // Audience options come from the resources the API actually returns.
  const audiences = useMemo(() => {
    const seen = new Set<string>();
    items.forEach((r) => {
      if (r.audience) seen.add(r.audience);
    });
    return [...seen].sort();
  }, [items]);

  return (
    <div className="container">
      <h1>Student Resources</h1>
      <p className="lede">
        Resources from the Center for Belonging at Cornell Bowers CIS —
        office services, community resources, and campus partners. Search
        and filter for your situation.
      </p>
      <div className="controls">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search resources…"
          aria-label="Search resources"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {RESOURCE_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={audience}
          onChange={(e) => setAudience(e.target.value)}
          aria-label="Filter by audience"
        >
          <option value="">All audiences</option>
          {audiences.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        {items.map((r) => (
          <article className="card" key={r.id}>
            <h3>{r.title}</h3>
            <p>{r.description}</p>
            <div className="tags">
              <span className="tag">{r.category}</span>
              {r.audience && <span className="tag neutral">{r.audience}</span>}
            </div>
            {r.link && (
              <p>
                <a href={r.link} target="_blank" rel="noopener">
                  Visit resource →
                </a>
              </p>
            )}
          </article>
        ))}
      </div>
      {!error && items.length === 0 && (
        <p>No resources match those filters yet.</p>
      )}
      <p className="lede">
        Source:{" "}
        <a
          href="https://bowers.cornell.edu/belonging-bowers/resources-and-support"
          target="_blank"
          rel="noopener"
        >
          Belonging at Bowers — Resources and Support
        </a>
        . Questions? Email{" "}
        <a href="mailto:deib-office@bowers.cornell.edu">
          deib-office@bowers.cornell.edu
        </a>
        .
      </p>
    </div>
  );
}
