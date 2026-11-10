"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  getToken,
  type Appointment,
  type DashboardData,
  type OutreachEntry,
  type User,
} from "../../lib/api";
import { BarChart, LineChart } from "../../components/Charts";

function SummaryTable({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <p>No report data yet.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([k, v]) => (
          <tr key={k}>
            <td>{k}</td>
            <td>
              {typeof v === "object" && v !== null
                ? JSON.stringify(v)
                : String(v)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [outreach, setOutreach] = useState<OutreachEntry[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    program: "",
    contacts_reached: "",
    notes: "",
  });

  const refresh = useCallback(() => {
    Promise.all([
      api.dashboard(),
      api.appointments(),
      api.outreachList(),
      api.reportsSummary(),
    ])
      .then(([d, a, o, s]) => {
        setData(d);
        setAppointments(a);
        setOutreach(o);
        setSummary(s);
      })
      .catch(() =>
        setError("Could not reach the API. Is the backend running?")
      );
  }, []);

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

  async function setAppointmentStatus(id: number, status: string) {
    try {
      await api.updateAppointment(id, status);
      refresh();
    } catch {
      setError("Could not update that appointment.");
    }
  }

  async function submitOutreach(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.addOutreach({
        date: form.date,
        program: form.program,
        contacts_reached: Number(form.contacts_reached) || 0,
        notes: form.notes,
      });
      setForm({
        date: new Date().toISOString().slice(0, 10),
        program: "",
        contacts_reached: "",
        notes: "",
      });
      refresh();
    } catch {
      setError("Could not save that entry. Check the API and try again.");
    }
  }

  if (!authChecked) return <div className="container"><p>Loading…</p></div>;

  if (!user) {
    return (
      <div className="container">
        <h1>Staff Dashboard</h1>
        <p className="error">
          This dashboard is staff only. Please{" "}
          <Link href="/login">log in</Link> with a staff account.
        </p>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="container">
        <h1>Staff Dashboard</h1>
        <p className="error">
          This dashboard is staff only. You are logged in as {user.name} (
          {user.role}). Staff roles are granted by an admin.
        </p>
      </div>
    );
  }

  const t = data?.totals;
  return (
    <div className="container">
      <h1>Staff Dashboard</h1>
      <p className="lede">Logged in as {user.name} (admin).</p>
      {error && <p className="error">{error}</p>}

      <h2>Overview</h2>
      <div className="stats">
        <div className="stat"><strong>{t?.subscribers ?? "—"}</strong><span>Newsletter subscribers</span></div>
        <div className="stat"><strong>{t?.confirmed_subscribers ?? "—"}</strong><span>Confirmed subscribers</span></div>
        <div className="stat"><strong>{t?.appointments_pending ?? "—"}</strong><span>Appointments pending</span></div>
        <div className="stat"><strong>{t?.resources ?? "—"}</strong><span>Resources</span></div>
        <div className="stat"><strong>{t?.conferences ?? "—"}</strong><span>Conferences</span></div>
        <div className="stat"><strong>{t?.events ?? "—"}</strong><span>Events</span></div>
        <div className="stat"><strong>{t?.participation_total ?? "—"}</strong><span>Total participation</span></div>
        <div className="stat"><strong>{t?.outreach_contacts ?? "—"}</strong><span>Outreach contacts</span></div>
      </div>

      {data && data.participation_by_conference.length > 0 && (
        <div className="card">
          <h3>Participation by conference</h3>
          <BarChart
            data={data.participation_by_conference}
            labelKey="conference"
            valueKey="count"
          />
        </div>
      )}

      {data && data.outreach_by_month.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>Outreach by month (contacts)</h3>
          <BarChart
            data={data.outreach_by_month}
            labelKey="month"
            valueKey="contacts"
          />
        </div>
      )}

      {data && data.subscribers_by_month.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>Subscriber growth</h3>
          <LineChart
            data={data.subscribers_by_month}
            labelKey="month"
            valueKey="count"
          />
        </div>
      )}

      {data && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>Appointments by status</h3>
          <p>
            Pending: {data.appointments_by_status.pending} · Confirmed:{" "}
            {data.appointments_by_status.confirmed} · Declined:{" "}
            {data.appointments_by_status.declined} · Completed:{" "}
            {data.appointments_by_status.completed}
          </p>
        </div>
      )}

      <h2>Appointments</h2>
      {appointments.length === 0 ? (
        <p>No appointment requests yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Topic</th>
              <th>Preferred</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((a) => (
              <tr key={a.id}>
                <td>{a.name}</td>
                <td>{a.email}</td>
                <td>{a.topic}</td>
                <td>
                  {a.preferred_date ?? "—"}
                  {a.preferred_time ? ` ${a.preferred_time}` : ""}
                </td>
                <td>{a.status}</td>
                <td>
                  <button
                    onClick={() => setAppointmentStatus(a.id, "confirmed")}
                    disabled={a.status === "confirmed"}
                  >
                    Confirm
                  </button>{" "}
                  <button
                    className="secondary"
                    onClick={() => setAppointmentStatus(a.id, "declined")}
                    disabled={a.status === "declined"}
                  >
                    Decline
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Outreach log</h2>
      <form className="form" onSubmit={submitOutreach}>
        <h3 style={{ margin: 0 }}>Add an outreach entry</h3>
        <label>
          Date
          <input
            type="date"
            required
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />
        </label>
        <label>
          Program
          <input
            required
            value={form.program}
            onChange={(e) => setForm({ ...form, program: e.target.value })}
            placeholder="e.g. Code Afrique"
          />
        </label>
        <label>
          Contacts reached
          <input
            type="number"
            min="0"
            value={form.contacts_reached}
            onChange={(e) =>
              setForm({ ...form, contacts_reached: e.target.value })
            }
            placeholder="0"
          />
        </label>
        <label>
          Notes
          <textarea
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="What happened, who it served, what worked"
          />
        </label>
        <button type="submit">Add entry</button>
      </form>
      {outreach.length === 0 ? (
        <p>No outreach entries yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Program</th>
              <th>Reached</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {outreach.map((e) => (
              <tr key={e.id}>
                <td>{e.date}</td>
                <td>{e.program}</td>
                <td>{e.contacts_reached}</td>
                <td>{e.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Leadership report</h2>
      {summary ? (
        <SummaryTable data={summary} />
      ) : (
        <p>No report data yet.</p>
      )}
    </div>
  );
}
