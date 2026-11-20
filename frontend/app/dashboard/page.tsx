"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  getToken,
  type Booking,
  type DashboardData,
  type OutreachEntry,
  type Slot,
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
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [outreach, setOutreach] = useState<OutreachEntry[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    program: "",
    contacts_reached: "",
    notes: "",
  });
  const [slotForm, setSlotForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    start_time: "14:00",
    end_time: "14:30",
    type: "call",
  });

  const refresh = useCallback(() => {
    Promise.all([
      api.dashboard(),
      api.bookings(),
      api.slots(false),
      api.outreachList(),
      api.reportsSummary(),
    ])
      .then(([d, b, s, o, sum]) => {
        setData(d);
        setBookings(b);
        setSlots(s);
        setOutreach(o);
        setSummary(sum);
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

  async function cancelBooking(id: number) {
    try {
      await api.cancelBooking(id);
      refresh();
    } catch {
      setError("Could not cancel that booking.");
    }
  }

  async function addSlot(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.createSlot(slotForm);
      setSlotForm({
        date: new Date().toISOString().slice(0, 10),
        start_time: "14:00",
        end_time: "14:30",
        type: "call",
      });
      refresh();
    } catch {
      setError("Could not add that slot. Check the times and try again.");
    }
  }

  async function deleteSlot(id: number) {
    try {
      await api.deleteSlot(id);
      refresh();
    } catch {
      setError("Could not delete that slot — cancel its booking first.");
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
        <div className="stat"><strong>{t?.audiences ?? "—"}</strong><span>Audiences</span></div>
        <div className="stat"><strong>{t?.contacts ?? "—"}</strong><span>Contacts to reach</span></div>
        <div className="stat"><strong>{t?.opted_out_contacts ?? "—"}</strong><span>Opted out</span></div>
        <div className="stat"><strong>{t?.campaigns ?? "—"}</strong><span>Newsletter issues</span></div>
        <div className="stat"><strong>{t?.campaigns_sent ?? "—"}</strong><span>Issues sent</span></div>
        <div className="stat"><strong>{t?.open_slots ?? "—"}</strong><span>Open appointment slots</span></div>
        <div className="stat"><strong>{t?.upcoming_bookings ?? "—"}</strong><span>Upcoming bookings</span></div>
        <div className="stat"><strong>{t?.subscribers ?? "—"}</strong><span>Newsletter subscribers</span></div>
        <div className="stat"><strong>{t?.confirmed_subscribers ?? "—"}</strong><span>Confirmed subscribers</span></div>
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
        <div className="grid">
          <div className="card">
            <h3>Appointments — slots</h3>
            <p>
              Open: {data.slots_by_status.open} · Booked:{" "}
              {data.slots_by_status.booked}
            </p>
            <p>
              <Link href="/appointments">Public booking page →</Link>
            </p>
          </div>
          <div className="card">
            <h3>Appointments — bookings</h3>
            <p>
              Booked: {data.bookings_by_status.booked} · Cancelled:{" "}
              {data.bookings_by_status.cancelled}
            </p>
          </div>
          <div className="card">
            <h3>Newsletter issues</h3>
            <p>
              Draft: {data.campaigns_by_status.draft} · Ready to send:{" "}
              {data.campaigns_by_status.queued} · Sent:{" "}
              {data.campaigns_by_status.sent} · Partially sent:{" "}
              {data.campaigns_by_status.partially_sent}
            </p>
            <p>
              <Link href="/campaigns">Compose an issue →</Link>
            </p>
          </div>
          <div className="card">
            <h3>Audiences</h3>
            <p>
              {data.totals.audiences} audiences · {data.totals.contacts}{" "}
              contacts · {data.totals.opted_out_contacts} opted out
            </p>
            <p>
              <Link href="/audiences">Manage audiences →</Link>
            </p>
          </div>
        </div>
      )}

      <h2>Availability slots (Dr. Roberts)</h2>
      <form className="form" onSubmit={addSlot}>
        <h3 style={{ margin: 0 }}>Add an availability slot</h3>
        <label>
          Date
          <input
            type="date"
            required
            value={slotForm.date}
            onChange={(e) => setSlotForm({ ...slotForm, date: e.target.value })}
          />
        </label>
        <label>
          Start time
          <input
            type="time"
            required
            value={slotForm.start_time}
            onChange={(e) =>
              setSlotForm({ ...slotForm, start_time: e.target.value })
            }
          />
        </label>
        <label>
          End time
          <input
            type="time"
            required
            value={slotForm.end_time}
            onChange={(e) =>
              setSlotForm({ ...slotForm, end_time: e.target.value })
            }
          />
        </label>
        <label>
          Type
          <select
            value={slotForm.type}
            onChange={(e) => setSlotForm({ ...slotForm, type: e.target.value })}
          >
            <option value="call">Call</option>
            <option value="in-person">In person</option>
          </select>
        </label>
        <button type="submit">Add slot</button>
      </form>
      {slots.length === 0 ? (
        <p>No slots yet. Add Dr. Roberts&apos; availability above — the booking page lists only open slots.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Time</th>
              <th>Type</th>
              <th>Host</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {slots.map((s) => (
              <tr key={s.id}>
                <td>{s.date}</td>
                <td>
                  {s.start_time}–{s.end_time}
                </td>
                <td>{s.type}</td>
                <td>{s.host}</td>
                <td>{s.status}</td>
                <td>
                  {s.status === "open" && (
                    <button className="secondary" onClick={() => deleteSlot(s.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Bookings</h2>
      {bookings.length === 0 ? (
        <p>No bookings yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Purpose</th>
              <th>When</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {bookings.map((b) => (
              <tr key={b.id}>
                <td>{b.name}</td>
                <td>{b.email}</td>
                <td>{b.purpose}</td>
                <td>
                  {b.slot
                    ? `${b.slot.date}, ${b.slot.start_time}–${b.slot.end_time} (${b.slot.type})`
                    : "—"}
                </td>
                <td>{b.status}</td>
                <td>
                  {b.status === "booked" && (
                    <button className="secondary" onClick={() => cancelBooking(b.id)}>
                      Cancel (re-opens slot)
                    </button>
                  )}
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
