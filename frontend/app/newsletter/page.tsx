"use client";

import { useState } from "react";
import { api } from "../../lib/api";

const INTEREST_OPTIONS = [
  "Conferences (Grace Hopper, Tapia, Code Afrique)",
  "Programs and events",
  "Resources and support",
  "Mentorship",
  "Career opportunities",
];

const TOPIC_OPTIONS = [
  "Grace Hopper",
  "Tapia",
  "Code Afrique",
  "CSMore",
  "Belonging at Bowers Awards",
  "General Center news",
];

const SOURCE_OPTIONS = [
  "Center for Belonging event",
  "Student organization (e.g. NSBE, URMC)",
  "CampusGroups",
  "A friend or classmate",
  "Cornell Bowers website",
  "Other",
];

function toggle(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((v) => v !== value)
    : [...list, value];
}

export default function NewsletterPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    source: "",
  });
  const [interests, setInterests] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [successMsg, setSuccessMsg] = useState("");
  const [error, setError] = useState("");
  const [unsubEmail, setUnsubEmail] = useState("");
  const [unsubResult, setUnsubResult] = useState("");

  async function submitSignup(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    if (!form.email.trim().toLowerCase().endsWith("@cornell.edu")) {
      setError("Use your Cornell email to subscribe.");
      return;
    }
    try {
      const res = await api.newsletterSignup({
        name: form.name,
        email: form.email,
        interests,
        topics,
        source: form.source,
      });
      // Single opt-in: the signup itself subscribes — no second step.
      if (res.already_subscribed) {
        setSuccessMsg(
          "You are already subscribed with that email — the next issue will land in your inbox."
        );
      } else if (res.email_sent) {
        setSuccessMsg(
          `You're subscribed — a welcome email is on its way to ${form.email}.`
        );
      } else {
        setSuccessMsg("You're subscribed — welcome to Open Door.");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      let detail = "";
      try {
        detail = JSON.parse(msg.slice(msg.indexOf("{"))).detail ?? "";
      } catch {
        detail = "";
      }
      setError(
        detail ||
          (msg.includes("Cornell")
            ? "Use your Cornell email to subscribe."
            : "Could not sign up. Check the API and try again.")
      );
    }
  }

  async function submitUnsubscribe(e: React.FormEvent) {
    e.preventDefault();
    setUnsubResult("");
    try {
      await api.newsletterUnsubscribe(unsubEmail);
      setUnsubResult(`Unsubscribed ${unsubEmail}.`);
      setUnsubEmail("");
    } catch {
      setUnsubResult("Unsubscribe failed. Check the email and try again.");
    }
  }

  return (
    <div className="container">
      <h1>The Center&apos;s newsletter</h1>
      <p className="lede">
        This is how the Center&apos;s resources reach students — each
        issue is sent to your Cornell inbox. The newsletter is the
        Center&apos;s core way of reaching the students who need it.
      </p>
      <h2>What subscribers get</h2>
      <ul>
        <li>
          <strong>Resources, featured in every issue</strong> — the
          Center&apos;s real office services, community resources, and
          campus partners, picked for that issue.
        </li>
        <li>
          <strong>Conference funding and deadlines</strong> — Grace
          Hopper, Tapia, Code Afrique, and what you need to apply.
        </li>
        <li>
          <strong>Events and programs</strong> — what the Center is
          running and how to take part.
        </li>
      </ul>
      <p className="notice">
        Signup is opt-in only and Cornell-only — use your @cornell.edu
        email. The Center also reaches students through audiences built
        with student organizations&apos; agreement (see{" "}
        <a href="/audiences">Audiences</a>). Either way, anyone can opt
        out and is never emailed again.
      </p>
      {successMsg && <p className="success">{successMsg}</p>}
      {error && <p className="error">{error}</p>}

      {!successMsg && (
<form className="form" onSubmit={submitSignup}>
            <h3 style={{ margin: 0 }}>Sign up for the newsletter</h3>
            <label>
              Name
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label>
              Cornell email
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="netid@cornell.edu"
              />
              <span>Cornell email only — use your @cornell.edu address.</span>
            </label>
            <label>
              Interests
              <span>What do you want to hear about?</span>
              <span className="checkbox-group">
                {INTEREST_OPTIONS.map((opt) => (
                  <label key={opt}>
                    <input
                      type="checkbox"
                      checked={interests.includes(opt)}
                      onChange={() => setInterests(toggle(interests, opt))}
                    />
                    {opt}
                  </label>
                ))}
              </span>
            </label>
            <label>
              Topics
              <span>Which programs should we highlight for you?</span>
              <span className="checkbox-group">
                {TOPIC_OPTIONS.map((opt) => (
                  <label key={opt}>
                    <input
                      type="checkbox"
                      checked={topics.includes(opt)}
                      onChange={() => setTopics(toggle(topics, opt))}
                    />
                    {opt}
                  </label>
                ))}
              </span>
            </label>
            <label>
              How did you hear about us?
              <select
                required
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
              >
                <option value="">Choose one…</option>
                {SOURCE_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">Sign up</button>
          </form>
      )}

      <h2>Unsubscribe</h2>
      <p className="lede">
        Every newsletter email includes a one-click unsubscribe link. You
        can also unsubscribe here.
      </p>
      <form className="form" onSubmit={submitUnsubscribe}>
        <label>
          Email
          <input
            type="email"
            required
            value={unsubEmail}
            onChange={(e) => setUnsubEmail(e.target.value)}
            placeholder="netid@cornell.edu"
          />
        </label>
        <button type="submit" className="secondary">
          Unsubscribe
        </button>
      </form>
      {unsubResult && <p className="notice">{unsubResult}</p>}
    </div>
  );
}
