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

export default function CampaignsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    subject: "",
    body: "",
    sender_name: "Center for Belonging",
    org_filter: "",
    interest_filter: "",
    include_self_signup: true,
  });
  const [pickedAudiences, setPickedAudiences] = useState<number[]>([]);
  const [pickedResources, setPickedResources] = useState<number[]>([]);

  const refresh = useCallback(async () => {
    try {
      const [list, auds, res] = await Promise.all([
        api.campaigns(),
        api.audiences(),
        api.resources(),
      ]);
      setCampaigns(list);
      setAudiences(auds);
      setResources(res);
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
  }

  function toggleResource(id: number) {
    setPickedResources((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function createCampaign(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    try {
      const created = await api.createCampaign({
        subject: form.subject,
        body: form.body,
        sender_name: form.sender_name,
        resource_ids: pickedResources,
        audience_ids: pickedAudiences,
        org_filter: form.org_filter,
        interest_filter: form.interest_filter,
        include_self_signup: form.include_self_signup,
      });
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
      setNotice(
        `Draft created — ${created.recipient_count} recipients match (opted-out excluded).`
      );
      refresh();
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("400")
          ? "Pick at least one audience, an organization filter, or newsletter subscribers, and fill in subject and body."
          : "Could not create that issue."
      );
    }
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
      if (result.smtp_configured === false) {
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

  if (!authChecked) return <div className="container"><p>Loading…</p></div>;

  if (!user || user.role !== "admin") {
    return (
      <div className="container">
        <h1>Newsletter issues</h1>
        <p className="error">
          Issues are staff only. Please{" "}
          <Link href="/login">log in</Link> with a staff account.
        </p>
        <p className="lede">
          Each issue is the Center&apos;s newsletter, built from its real
          resources. Staff pick the resources to feature, write the
          message, choose who receives it — subscribers and/or an
          audience — preview the exact recipient list, and send.
        </p>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Newsletter issues</h1>
      <p className="lede">
        Each issue is the Center&apos;s newsletter, built from its real
        resources. Pick the resources to feature, write your message,
        choose who receives it — newsletter subscribers and/or an
        audience — preview the exact recipient list (opted-out contacts
        are always excluded), then send.
      </p>
      {error && <p className="error">{error}</p>}
      {notice && <p className="success">{notice}</p>}

      <h2>Compose an issue</h2>
      <form className="form" onSubmit={createCampaign}>
        <label>
          Subject
          <input
            required
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            placeholder="e.g. Tapia 2026 — funding and deadlines"
          />
        </label>
        <label>
          Message
          <textarea
            required
            rows={6}
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            placeholder="What should subscribers hear?"
          />
        </label>
        <label>
          Featured resources
          <span>
            Pick the Center&apos;s real resources to feature in this
            issue — they are listed with their links in the email.
          </span>
          <span className="checkbox-group">
            {resources.length === 0 && <span>Loading resources…</span>}
            {resources.map((r) => (
              <label key={r.id}>
                <input
                  type="checkbox"
                  checked={pickedResources.includes(r.id)}
                  onChange={() => toggleResource(r.id)}
                />
                {r.title} ({r.category})
                {r.link ? ` — ${r.link}` : ""}
              </label>
            ))}
          </span>
        </label>
        <label>
          Sender name
          <input
            value={form.sender_name}
            onChange={(e) =>
              setForm({ ...form, sender_name: e.target.value })
            }
          />
        </label>
        <label>
          Audiences
          <span className="checkbox-group">
            {audiences.length === 0 && <span>No audiences yet — create one on the Audiences page.</span>}
            {audiences.map((a) => (
              <label key={a.id}>
                <input
                  type="checkbox"
                  checked={pickedAudiences.includes(a.id)}
                  onChange={() => toggleAudience(a.id)}
                />
                {a.name} ({a.contact_count - a.opted_out_count} reachable)
              </label>
            ))}
          </span>
        </label>
        <label>
          Organization filter
          <span>Only contacts from this org, e.g. NSBE. Leave blank for all selected audiences.</span>
          <input
            value={form.org_filter}
            onChange={(e) => setForm({ ...form, org_filter: e.target.value })}
          />
        </label>
        <label>
          Interest filter
          <span>Only contacts whose interests include this, e.g. Tapia. Leave blank for all.</span>
          <input
            value={form.interest_filter}
            onChange={(e) =>
              setForm({ ...form, interest_filter: e.target.value })
            }
          />
        </label>
        <label>
          <span className="checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={form.include_self_signup}
                onChange={(e) =>
                  setForm({
                    ...form,
                    include_self_signup: e.target.checked,
                  })
                }
              />
              Send to confirmed newsletter subscribers (the newsletter
              list) — on by default; an issue can go to subscribers
              alone, with no audience picked.
            </label>
          </span>
        </label>
        <button type="submit">Create draft issue</button>
      </form>

      <h2>All issues</h2>
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
                  <button className="secondary" onClick={() => openCampaign(c.id)}>
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
              No email server is configured. Set SMTP_HOST, SMTP_PORT,
              SMTP_USER, SMTP_PASS, and SMTP_FROM in the Render dashboard
              (a Gmail app password or SendGrid works), then send again.
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
              {selected.status === "queued" ? "Try sending again" : "Send issue"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
