"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  getToken,
  type Audience,
  type AudienceDetail,
  type OrgSubmission,
  type User,
} from "../../lib/api";
import StaffTabs from "../../components/StaffTabs";

/* Staff board — Audiences (mockup 02, second tab).
 * Top: the mockup's review list — organizations that shared their
 * lists wait here; staff Approve / Decline each one (existing
 * reviewOrgSubmission API; the API has no un-review, so settled rows
 * show their result without the mockup's Undo — see APPLY_NOTES.md).
 * Below, unchanged in capability: create an audience, all audiences,
 * and per-audience management (add contact, CSV upload, contacts). */

const ORG_SUGGESTIONS = ["NSBE", "URMC", "CampusGroups"];

export default function AudiencesPage() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [selected, setSelected] = useState<AudienceDetail | null>(null);
  const [submissions, setSubmissions] = useState<OrgSubmission[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [newAudience, setNewAudience] = useState({
    name: "",
    source_org: "",
    description: "",
  });
  const [contactForm, setContactForm] = useState({
    name: "",
    email: "",
    source_org: "",
    interests: "",
  });
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{
    valid_rows: number;
    invalid_rows: number;
    errors: { row: number | null; reason: string }[];
    sample: { name: string; email: string; interests: string[] }[];
  } | null>(null);
  const [importResult, setImportResult] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [list, subs] = await Promise.all([
        api.audiences(),
        api.orgSubmissions(),
      ]);
      setAudiences(list);
      setSubmissions(subs);
      if (selected) {
        const detail = await api.audience(selected.id);
        setSelected(detail);
      }
    } catch {
      setError("Could not reach the API. Is the backend running?");
    }
  }, [selected]);

  useEffect(() => {
    if (!getToken()) {
      setAuthChecked(true);
      return;
    }
    api
      .me()
      .then((u) => {
        setUser(u);
        setAuthChecked(true);
        if (u.role === "admin") refresh();
      })
      .catch(() => setAuthChecked(true));
  }, [refresh]);

  async function createAudience(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    try {
      await api.createAudience(newAudience);
      setNewAudience({ name: "", source_org: "", description: "" });
      setNotice("Audience created.");
      refresh();
    } catch {
      setError("Could not create that audience.");
    }
  }

  async function openAudience(id: number) {
    setError("");
    try {
      setSelected(await api.audience(id));
      setPreview(null);
      setImportResult("");
      setCsvFile(null);
    } catch {
      setError("Could not load that audience.");
    }
  }

  async function addContact(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setError("");
    try {
      await api.addContact(selected.id, {
        name: contactForm.name,
        email: contactForm.email,
        source_org: contactForm.source_org,
        interests: contactForm.interests
          .split(";")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setContactForm({ name: "", email: "", source_org: "", interests: "" });
      refresh();
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("409")
          ? "That email is already in this audience."
          : "Could not add that contact. Check the email and try again."
      );
    }
  }

  async function setOptOut(contactId: number, optedOut: boolean) {
    if (!selected) return;
    try {
      await api.updateContact(selected.id, contactId, { opted_out: optedOut });
      refresh();
    } catch {
      setError("Could not update that contact.");
    }
  }

  async function removeContact(contactId: number) {
    if (!selected) return;
    try {
      await api.deleteContact(selected.id, contactId);
      refresh();
    } catch {
      setError("Could not delete that contact.");
    }
  }

  async function downloadTemplate() {
    try {
      const text = await api.contactsTemplate();
      const blob = new Blob([text], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "contacts-template.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not download the template.");
    }
  }

  async function runPreview() {
    if (!selected || !csvFile) return;
    setError("");
    setImportResult("");
    try {
      const result = await api.uploadContacts(selected.id, csvFile, true);
      setPreview({
        valid_rows: result.valid_rows ?? 0,
        invalid_rows: result.invalid_rows ?? 0,
        errors: result.errors ?? [],
        sample: result.sample ?? [],
      });
    } catch {
      setError("Could not read that file. It must be a CSV file.");
    }
  }

  async function confirmImport() {
    if (!selected || !csvFile) return;
    setError("");
    try {
      const result = await api.uploadContacts(selected.id, csvFile, false);
      setImportResult(
        `Imported ${result.imported ?? 0} contacts` +
          (result.skipped ? `, skipped ${result.skipped}.` : ".")
      );
      setPreview(null);
      setCsvFile(null);
      refresh();
    } catch {
      setError("Import failed. Check the file and try again.");
    }
  }

  async function reviewSubmission(
    id: number,
    decision: "approve" | "reject",
    audienceId?: number
  ) {
    setError("");
    setNotice("");
    try {
      const result = await api.reviewOrgSubmission(id, {
        decision,
        audience_id: audienceId,
      });
      setNotice(
        decision === "approve"
          ? `Approved — ${result.contacts_added ?? 0} contacts added to an audience.`
          : "Submission declined."
      );
      refresh();
    } catch {
      setError("Could not review that submission.");
    }
  }

  if (!authChecked)
    return (
      <div className="od-staff-wrap">
        <p>Loading…</p>
      </div>
    );

  if (!user || user.role !== "admin") {
    return (
      <div className="od-staff-wrap">
        <h1 className="od-board-title">Audiences</h1>
        <p className="error" style={{ marginTop: 16 }}>
          Audiences are staff only. Please <Link href="/login">sign in</Link>{" "}
          with a staff account.
        </p>
        <p className="lede">
          Audiences are the groups the Center reaches — built from student
          organization lists shared with the org&apos;s agreement, manual
          adds, and org representatives&apos; submissions.
        </p>
      </div>
    );
  }

  const pending = submissions.filter((s) => s.status === "pending");
  const reviewed = submissions.filter((s) => s.status !== "pending");
  const approvedContacts = audiences.reduce(
    (t, a) => t + a.contact_count,
    0
  );

  return (
    <div className="od-staff-wrap">
      <StaffTabs active="audiences" />
      {error && (
        <p className="error" style={{ marginTop: 16 }}>
          {error}
        </p>
      )}
      {notice && (
        <p className="success" style={{ marginTop: 16 }}>
          {notice}
        </p>
      )}

      <section style={{ marginTop: 28 }}>
        <h1 className="od-board-title">Audiences</h1>
        <p className="lede" style={{ marginTop: 14 }}>
          Student organizations share their lists with the Center, and
          nobody is added without approval. Lists sent in by an
          organization wait here for review.
        </p>

        <div className="od-list-rows">
          {pending.length === 0 && reviewed.length === 0 && (
            <p style={{ padding: "16px 8px" }}>
              No organization lists have been submitted yet.
            </p>
          )}
          {pending.map((s) => (
            <div className="od-list-row" key={s.id}>
              <div className="row-main">
                <div className="row-title">{s.org_name}</div>
                <div className="row-sub">
                  Submitted by {s.rep_name || s.rep_email}
                  {s.rep_name ? ` (${s.rep_email})` : ""},{" "}
                  {s.contacts.length} contacts
                  {s.notes ? ` — ${s.notes}` : ""}
                </div>
              </div>
              <div className="row-actions">
                <button onClick={() => reviewSubmission(s.id, "approve")}>
                  Approve
                </button>
                <button
                  className="secondary"
                  onClick={() => reviewSubmission(s.id, "reject")}
                >
                  Decline
                </button>
              </div>
            </div>
          ))}
          {reviewed.map((s) => (
            <div className="od-list-row" key={s.id}>
              <div className="row-main">
                <div className="row-title">{s.org_name}</div>
                <div className="row-sub">
                  Submitted by {s.rep_name || s.rep_email},{" "}
                  {s.contacts.length} contacts
                </div>
              </div>
              <div className="row-actions">
                <span style={{ fontWeight: 600 }}>
                  {s.status === "approved" ? "Approved" : "Declined"}
                  {s.status === "approved" && s.contacts_added != null
                    ? ` — ${s.contacts_added} contacts added`
                    : ""}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p style={{ margin: "18px 0 0", color: "var(--secondary)" }}>
          Approved contacts across organizations:{" "}
          <strong>{approvedContacts}</strong>
        </p>
      </section>

      <h2 style={{ marginTop: 56 }}>Create an audience</h2>
      <form className="form" onSubmit={createAudience}>
        <label>
          Audience name
          <input
            required
            value={newAudience.name}
            onChange={(e) =>
              setNewAudience({ ...newAudience, name: e.target.value })
            }
            placeholder="e.g. NSBE members"
          />
        </label>
        <label>
          Source organization
          <span>NSBE, URMC, CampusGroups, or a custom org name.</span>
          <input
            value={newAudience.source_org}
            onChange={(e) =>
              setNewAudience({ ...newAudience, source_org: e.target.value })
            }
            placeholder="e.g. NSBE"
            list="org-suggestions"
          />
          <datalist id="org-suggestions">
            {ORG_SUGGESTIONS.map((o) => (
              <option key={o} value={o} />
            ))}
          </datalist>
        </label>
        <label>
          Description
          <input
            value={newAudience.description}
            onChange={(e) =>
              setNewAudience({ ...newAudience, description: e.target.value })
            }
          />
        </label>
        <button type="submit">Create audience</button>
      </form>

      <h2>All audiences</h2>
      {audiences.length === 0 ? (
        <p>
          No audiences yet. Create one above, or wait for an org to submit
          its contacts.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Source org</th>
              <th>Contacts</th>
              <th>Opted out</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {audiences.map((a) => (
              <tr key={a.id}>
                <td>{a.name}</td>
                <td>{a.source_org || "—"}</td>
                <td>{a.contact_count}</td>
                <td>{a.opted_out_count}</td>
                <td>
                  <button
                    className="secondary"
                    onClick={() => openAudience(a.id)}
                  >
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <>
          <h2>{selected.name}</h2>
          <p className="lede">
            {selected.contact_count} contacts · {selected.opted_out_count}{" "}
            opted out. Opted-out contacts are excluded from every issue.
          </p>

          <h3>Add a contact</h3>
          <form className="form" onSubmit={addContact}>
            <label>
              Name
              <input
                value={contactForm.name}
                onChange={(e) =>
                  setContactForm({ ...contactForm, name: e.target.value })
                }
              />
            </label>
            <label>
              Email
              <input
                type="email"
                required
                value={contactForm.email}
                onChange={(e) =>
                  setContactForm({ ...contactForm, email: e.target.value })
                }
                placeholder="netid@cornell.edu"
              />
            </label>
            <label>
              Organization
              <input
                value={contactForm.source_org}
                onChange={(e) =>
                  setContactForm({ ...contactForm, source_org: e.target.value })
                }
                placeholder={selected.source_org || "e.g. NSBE"}
              />
            </label>
            <label>
              Interests
              <span>Separate with semicolons, e.g. Tapia; Mentorship</span>
              <input
                value={contactForm.interests}
                onChange={(e) =>
                  setContactForm({ ...contactForm, interests: e.target.value })
                }
              />
            </label>
            <button type="submit">Add contact</button>
          </form>

          <h3>Upload a CSV</h3>
          <p className="lede">
            Columns: <code>name, email, org, interests</code> (interests
            separated by semicolons).{" "}
            <button
              className="secondary"
              type="button"
              onClick={downloadTemplate}
            >
              Download template
            </button>
          </p>
          <div className="form">
            <label>
              CSV file
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  setCsvFile(e.target.files?.[0] ?? null);
                  setPreview(null);
                  setImportResult("");
                }}
              />
            </label>
            <button type="button" disabled={!csvFile} onClick={runPreview}>
              Preview import
            </button>
            {preview && (
              <div>
                <p>
                  <strong>{preview.valid_rows}</strong> rows will import,{" "}
                  <strong>{preview.invalid_rows}</strong> will be skipped.
                </p>
                {preview.errors.length > 0 && (
                  <ul>
                    {preview.errors.map((err, i) => (
                      <li key={i}>
                        Row {err.row ?? "?"}: {err.reason}
                      </li>
                    ))}
                  </ul>
                )}
                <button type="button" onClick={confirmImport}>
                  Import {preview.valid_rows} contacts
                </button>
              </div>
            )}
            {importResult && <p className="success">{importResult}</p>}
          </div>

          <h3>Contacts</h3>
          {selected.contacts.length === 0 ? (
            <p>No contacts in this audience yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Org</th>
                  <th>Interests</th>
                  <th>Source</th>
                  <th>Opted out</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {selected.contacts.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name || "—"}</td>
                    <td>{c.email}</td>
                    <td>{c.source_org || "—"}</td>
                    <td>{c.interests.join(", ") || "—"}</td>
                    <td>{c.source}</td>
                    <td>
                      <input
                        type="checkbox"
                        checked={c.opted_out}
                        onChange={(e) => setOptOut(c.id, e.target.checked)}
                        aria-label={`Opt out ${c.email}`}
                      />
                    </td>
                    <td>
                      <button
                        className="secondary"
                        onClick={() => removeContact(c.id)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
