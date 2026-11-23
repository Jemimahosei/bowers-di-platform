"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  getToken,
  type Audience,
  type Campaign,
  type Resource,
  type User,
} from "../../lib/api";
import StaffTabs from "../../components/StaffTabs";

/* Staff board — Issues (mockup 02, first tab).
 * Left: Write an issue — Subject, Opening note, Opportunities
 * checklist (the platform's real resources). Right: Who gets it —
 * confirmed subscribers always included, audiences with reachable
 * counts, live total with the mockup's duplicates/unsubscribed note,
 * then Review and send → confirm box → sent state.
 * Sending uses the existing two-step API: createCampaign (draft)
 * then sendCampaign. The All issues list and issue detail below keep
 * every existing capability (view recipients, send a draft later). */

type Phase = "draft" | "ask" | "sent";

export default function CampaignsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [subscriberCount, setSubscriberCount] = useState<number | null>(null);
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    subject: "",
    body: "",
    sender_name: "Center for Belonging",
    org_filter: "",
    interest_filter: "",
    include_self_signup: true, // mockup: subscribers always included
  });
  const [pickedAudiences, setPickedAudiences] = useState<number[]>([]);
  const [pickedResources, setPickedResources] = useState<number[]>([]);
  const [phase, setPhase] = useState<Phase>("draft");
  const [sending, setSending] = useState(false);
  const [sentInfo, setSentInfo] = useState<{
    sent: number;
    failed: number;
    queued: boolean;
  } | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [list, auds, res, dash] = await Promise.all([
        api.campaigns(),
        api.audiences(),
        api.resources(),
        api.dashboard().catch(() => null),
      ]);
      setCampaigns(list);
      setAudiences(auds);
      setResources(res);
      if (dash) setSubscriberCount(dash.totals.confirmed_subscribers);
      if (selected) {
        const detail = await api.campaign(selected.id);
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

  function toggleAudience(id: number) {
    setPickedAudiences((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
    setPhase("draft");
  }

  function toggleResource(id: number) {
    setPickedResources((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
    setPhase("draft");
  }

  /* Live estimate for the "Who gets it" panel. The backend dedupes by
   * email and skips opted-out contacts when the issue is created, so
   * the created draft's recipient_count is the exact number. */
  const audienceTotal = audiences
    .filter((a) => pickedAudiences.includes(a.id))
    .reduce((t, a) => t + Math.max(0, a.contact_count - a.opted_out_count), 0);
  const total = (subscriberCount ?? 0) + audienceTotal;

  async function reviewAndSend() {
    if (!form.subject.trim() || !form.body.trim()) {
      setError("Give the issue a subject and an opening note first.");
      return;
    }
    setError("");
    setPhase("ask");
  }

  async function sendNow() {
    setError("");
    setNotice("");
    setSending(true);
    try {
      const created = await api.createCampaign({
        subject: form.subject,
        body: form.body,
        sender_name: form.sender_name,
        resource_ids: pickedResources,
        audience_ids: pickedAudiences,
        org_filter: form.org_filter,
        interest_filter: form.interest_filter,
        include_self_signup: true,
      });
      const result = await api.sendCampaign(created.id);
      if (result.email_configured === false) {
        setSentInfo({ sent: 0, failed: 0, queued: true });
      } else {
        setSentInfo({
          sent: result.sent ?? 0,
          failed: result.failed ?? 0,
          queued: false,
        });
      }
      setPhase("sent");
      refresh();
    } catch (err) {
      setPhase("draft");
      setError(
        err instanceof Error && err.message.includes("400")
          ? "This issue has no recipients, or the subject/opening note is missing."
          : "Could not send that issue."
      );
    } finally {
      setSending(false);
    }
  }

  function writeAnother() {
    setForm({
      subject: "",
      body: "",
      sender_name: "Center for Belonging",
      org_filter: "",
      interest_filter: "",
      include_self_signup: true,
    });
    setPickedAudiences([]);
    setPickedResources([]);
    setSentInfo(null);
    setPhase("draft");
  }

  async function openCampaign(id: number) {
    setError("");
    try {
      setSelected(await api.campaign(id));
    } catch {
      setError("Could not load that campaign.");
    }
  }

  async function sendSelected() {
    if (!selected) return;
    setError("");
    setNotice("");
    try {
      const result = await api.sendCampaign(selected.id);
      if (result.email_configured === false) {
        setNotice(
          "No email server is configured, so this issue is saved as ready to send — nothing was sent. " +
            (result.message ?? "")
        );
      } else {
        setNotice(
          `Sent to ${result.sent ?? 0} recipients` +
            (result.failed ? `, ${result.failed} failed.` : ".")
        );
      }
      refresh();
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("400")
          ? "This issue has no recipients."
          : "Could not send that issue."
      );
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
        <h1 className="od-board-title">Newsletter issues</h1>
        <p className="error" style={{ marginTop: 16 }}>
          Issues are staff only. Please <Link href="/login">sign in</Link>{" "}
          with a staff account.
        </p>
        <p className="lede">
          Each issue is the Center&apos;s newsletter, built from its real
          resources. Staff pick the resources to feature, write the
          message, choose who receives it, preview the exact recipient
          list, and send.
        </p>
      </div>
    );
  }

  return (
    <div className="od-staff-wrap">
      <StaffTabs active="issues" />
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

      <div className="od-board-grid">
        <div className="od-board-main">
          <h1>Write an issue</h1>
          <label className="od-field-label" htmlFor="od-subject">
            Subject
          </label>
          <input
            id="od-subject"
            className="od-field"
            type="text"
            value={form.subject}
            onChange={(e) => {
              setForm({ ...form, subject: e.target.value });
              setPhase("draft");
            }}
            placeholder="e.g. Funding is open for two conferences"
          />
          <label className="od-field-label" htmlFor="od-intro">
            Opening note
          </label>
          <textarea
            id="od-intro"
            className="od-field"
            rows={3}
            value={form.body}
            onChange={(e) => {
              setForm({ ...form, body: e.target.value });
              setPhase("draft");
            }}
            placeholder="Here is what to apply for, and by when."
          />
          <fieldset style={{ margin: "22px 0 0", padding: 0, border: 0 }}>
            <legend style={{ padding: 0, fontWeight: 600, lineHeight: "24px" }}>
              Opportunities in this issue
            </legend>
            <div className="od-checkrows">
              {resources.length === 0 && (
                <p className="od-total-note" style={{ padding: "12px 8px" }}>
                  Loading resources…
                </p>
              )}
              {resources.map((r) => {
                const on = pickedResources.includes(r.id);
                return (
                  <button
                    key={r.id}
                    type="button"
                    className="od-checkrow"
                    role="checkbox"
                    aria-checked={on}
                    onClick={() => toggleResource(r.id)}
                  >
                    <span className="box" aria-hidden="true">
                      {on ? "✓" : ""}
                    </span>
                    <span className="row-main">
                      <span className="row-title">{r.title}</span>
                      <span className="row-sub">
                        {r.category}
                        {r.audience ? `, for ${r.audience}` : ""}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>

        <aside className="od-board-aside">
          <h2>Who gets it</h2>
          <fieldset style={{ margin: "14px 0 0", padding: 0, border: 0 }}>
            <legend
              style={{
                padding: 0,
                fontSize: 14,
                lineHeight: "22px",
                color: "var(--muted)",
              }}
            >
              Confirmed subscribers always included. Add audiences:
            </legend>
            <div style={{ marginTop: 6 }}>
              <div
                className="od-checkrow small"
                role="checkbox"
                aria-checked={true}
                aria-disabled="true"
                style={{ cursor: "default" }}
              >
                <span className="box" aria-hidden="true">
                  ✓
                </span>
                <span className="row-main">Confirmed subscribers</span>
                <span className="row-count">
                  {subscriberCount ?? "—"}
                </span>
              </div>
              {audiences.map((a) => {
                const on = pickedAudiences.includes(a.id);
                return (
                  <button
                    key={a.id}
                    type="button"
                    className="od-checkrow small"
                    role="checkbox"
                    aria-checked={on}
                    onClick={() => toggleAudience(a.id)}
                  >
                    <span className="box" aria-hidden="true">
                      {on ? "✓" : ""}
                    </span>
                    <span className="row-main">{a.name}</span>
                    <span className="row-count">
                      {Math.max(0, a.contact_count - a.opted_out_count)}
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="od-field-label" htmlFor="od-org-filter">
            Organization filter <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
          </label>
          <input
            id="od-org-filter"
            className="od-field"
            type="text"
            value={form.org_filter}
            onChange={(e) => setForm({ ...form, org_filter: e.target.value })}
            placeholder="e.g. NSBE — blank for all"
          />
          <label className="od-field-label" htmlFor="od-interest-filter">
            Interest filter <span style={{ color: "var(--muted)", fontWeight: 400 }}>(optional)</span>
          </label>
          <input
            id="od-interest-filter"
            className="od-field"
            type="text"
            value={form.interest_filter}
            onChange={(e) =>
              setForm({ ...form, interest_filter: e.target.value })
            }
            placeholder="e.g. Tapia — blank for all"
          />
          <label className="od-field-label" htmlFor="od-sender">
            Sender name
          </label>
          <input
            id="od-sender"
            className="od-field"
            type="text"
            value={form.sender_name}
            onChange={(e) =>
              setForm({ ...form, sender_name: e.target.value })
            }
          />

          <div className="od-total-row">
            <span>This issue goes to</span>
            <span>{total} people</span>
          </div>
          <p className="od-total-note">
            Duplicates are removed. Anyone who unsubscribed is skipped.
          </p>

          {phase === "draft" && (
            <button
              type="button"
              className="od-send-btn"
              onClick={reviewAndSend}
            >
              Review and send
            </button>
          )}
          {phase === "ask" && (
            <div className="od-ask-box" aria-live="polite">
              <div className="q">
                Send “{form.subject}” to {total} people?
              </div>
              <div className="sub">Sending cannot be undone.</div>
              <div className="od-ask-actions">
                <button type="button" onClick={sendNow} disabled={sending}>
                  {sending ? "Sending…" : "Send now"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setPhase("draft")}
                >
                  Keep editing
                </button>
              </div>
            </div>
          )}
          {phase === "sent" && sentInfo && (
            <div className="od-sent-box" aria-live="polite">
              {sentInfo.queued ? (
                <>
                  <div className="q">Saved as ready to send</div>
                  <div className="sub">
                    No email server is configured, so nothing was sent
                    yet. The issue is in your issues list below — send it
                    from there once email is connected.
                  </div>
                </>
              ) : (
                <>
                  <div className="q">Sent to {sentInfo.sent} people</div>
                  <div className="sub">
                    {sentInfo.failed
                      ? `${sentInfo.failed} could not be delivered. `
                      : ""}
                    It is saved in your sent issues, and it is now the
                    latest issue on the public page.
                  </div>
                </>
              )}
              <button
                type="button"
                className="secondary"
                style={{ marginTop: 12 }}
                onClick={writeAnother}
              >
                Write another
              </button>
            </div>
          )}
        </aside>
      </div>

      <h2 style={{ marginTop: 56 }}>All issues</h2>
      {campaigns.length === 0 ? (
        <p>No issues yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Subject</th>
              <th>Status</th>
              <th>Recipients</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id}>
                <td>{c.subject}</td>
                <td>{c.status}</td>
                <td>{c.recipient_count}</td>
                <td>
                  <button
                    className="secondary"
                    onClick={() => openCampaign(c.id)}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h3 style={{ marginTop: 0 }}>{selected.subject}</h3>
          <p>
            <strong>Status:</strong> {selected.status} ·{" "}
            <strong>From:</strong> {selected.sender_name} ·{" "}
            <strong>Recipients:</strong> {selected.recipient_count}
          </p>
          {selected.status === "queued" && (
            <p className="notice">
              <strong>Ready to send — nothing has been sent yet.</strong>{" "}
              No email server is configured. Set RESEND_API_KEY and
              RESEND_FROM in the Render dashboard (see DEPLOY_NOTES.md),
              then send again.
            </p>
          )}
          <p style={{ whiteSpace: "pre-wrap" }}>{selected.body}</p>
          {selected.featured_resources &&
            selected.featured_resources.length > 0 && (
              <>
                <h4>Featured resources in this issue</h4>
                <ul>
                  {selected.featured_resources.map((r) => (
                    <li key={r.id}>
                      {r.link ? (
                        <a href={r.link} target="_blank" rel="noopener">
                          {r.title}
                        </a>
                      ) : (
                        r.title
                      )}{" "}
                      ({r.category})
                    </li>
                  ))}
                </ul>
              </>
            )}
          <h4>Recipients</h4>
          {selected.recipients && selected.recipients.length > 0 ? (
            <ul>
              {selected.recipients.map((r) => (
                <li key={r.email}>
                  {r.name || r.email} &lt;{r.email}&gt; — {r.source}
                  {r.status ? ` — ${r.status}` : ""}
                  {r.error ? ` (${r.error})` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p>No recipients.</p>
          )}
          {(selected.status === "draft" || selected.status === "queued") && (
            <button onClick={sendSelected}>
              {selected.status === "queued"
                ? "Try sending again"
                : "Send issue"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
