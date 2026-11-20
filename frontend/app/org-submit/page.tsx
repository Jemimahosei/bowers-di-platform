"use client";

import { useState } from "react";
import { api } from "../../lib/api";

export default function OrgSubmitPage() {
  const [form, setForm] = useState({
    org_name: "",
    rep_name: "",
    rep_email: "",
    notes: "",
  });
  const [contactsText, setContactsText] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  function parsePasted(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name = "", email = "", interestsRaw = ""] = line
          .split(",")
          .map((s) => s.trim());
        return {
          name,
          email,
          interests: interestsRaw
            .split(";")
            .map((s) => s.trim())
            .filter(Boolean),
        };
      });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (csvFile) {
        await api.submitOrgContactsFile(form, csvFile);
      } else {
        const contacts = parsePasted(contactsText);
        if (contacts.length === 0) {
          setError("Add at least one contact — paste lines or upload a CSV.");
          return;
        }
        await api.submitOrgContacts({ ...form, contacts });
      }
      setSubmitted(true);
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("400")
          ? "Check the organization name, your email, and that every contact has a valid email."
          : "Could not send that submission. Try again."
      );
    }
  }

  return (
    <div className="container">
      <h1>Share your organization&apos;s contacts</h1>
      <p className="lede">
        Are you a representative of a student organization — NSBE, URMC,
        CampusGroups, or another group? Share your group&apos;s contacts so
        the Center for Belonging can reach them about resources,
        conferences, and opportunities.
      </p>
      <p className="notice">
        <strong>Your list stays yours.</strong> Submitting here does not
        hand over your roster — Center staff review every submission and
        approve it into an audience before anyone is contacted. Anyone on
        the list can opt out at any time, and opted-out contacts are never
        emailed.
      </p>
      {error && <p className="error">{error}</p>}
      {submitted ? (
        <div className="success">
          <h3 style={{ marginTop: 0 }}>Submission received</h3>
          <p>
            Thank you. Your submission is pending review — Center staff will
            look it over and approve it into an audience. Nothing is added
            automatically.
          </p>
        </div>
      ) : (
        <form className="form" onSubmit={submit}>
          <label>
            Organization
            <input
              required
              value={form.org_name}
              onChange={(e) => setForm({ ...form, org_name: e.target.value })}
              placeholder="e.g. NSBE"
            />
          </label>
          <label>
            Your name
            <input
              required
              value={form.rep_name}
              onChange={(e) => setForm({ ...form, rep_name: e.target.value })}
            />
          </label>
          <label>
            Your email
            <input
              type="email"
              required
              value={form.rep_email}
              onChange={(e) =>
                setForm({ ...form, rep_email: e.target.value })
              }
              placeholder="netid@cornell.edu"
            />
          </label>
          <label>
            Notes
            <span>Anything staff should know about this list.</span>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </label>
          <label>
            Contacts — paste lines
            <span>
              One per line: Name, email, interests (interests separated by
              semicolons). Example: Ada Lovelace, ada@cornell.edu, Tapia;
              Mentorship
            </span>
            <textarea
              rows={6}
              value={contactsText}
              onChange={(e) => setContactsText(e.target.value)}
              placeholder={"Ada Lovelace, ada@cornell.edu, Tapia; Mentorship"}
            />
          </label>
          <label>
            Or upload a CSV instead
            <span>Columns: name, email, org, interests.</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit">Submit contacts for review</button>
        </form>
      )}
    </div>
  );
}
