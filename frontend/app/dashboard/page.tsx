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
import StaffTabs from "../../components/StaffTabs";

/* Staff board — Times (mockup 02, third tab) + the rest of the staff
 * dashboard. The mockup's "Open times" board leads: the times
 * students see under Talk to Dr. Roberts, booked times protected from
 * removal, and an Add a time card. The API needs a real date and
 * start/end times, so the card keeps date/time inputs where the
 * mockup sketches free-text Day/Time (see APPLY_NOTES.md). Bookings,
 * overview stats, charts, outreach log and the leadership report
 * follow, unchanged in capability. */

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

function fmtTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  if (Number.isNaN(h)) return hhmm;
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m ? `${h12}:${String(m).padStart(2, "0")} ${ampm}` : `${h12} ${ampm}`;
}

function slotDayLabel(slot: Slot): string {
  const d = new Date(`${slot.date}T12:00:00`);
  const day = d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  return `${day} · ${fmtTime(slot.start_time)}–${fmtTime(slot.end_time)}`;
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
  const [slotError, setSlotError] = useState("");
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
    setSlotError("");
    if (!slotForm.date || !slotForm.start_time || !slotForm.end_time) {
      setSlotError("Enter a day and both times.");
      return;
    }
    if (slotForm.end_time <= slotForm.start_time) {
      setSlotError("End time must be after start time.");
      return;
    }
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
      setSlotError("Could not add that time. Check the times and try again.");
    }
  }

  async function deleteSlot(id: number) {
    try {
      await api.deleteSlot(id);
      refresh();
    } catch {
      setError("Could not remove that time — cancel its booking first.");
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

  if (!authChecked)
    return (
      <div className="od-staff-wrap">
        <p>Loading…</p>
      </div>
    );

  if (!user) {
    return (
      <div className="od-staff-wrap">
        <h1 className="od-board-title">Staff Dashboard</h1>
        <p className="error" style={{ marginTop: 16 }}>
          This dashboard is staff only. Please{" "}
          <Link href="/login">sign in</Link> with a staff account.
        </p>
      </div>
    );
  }

  if (user.role !== "admin") {
    return (
      <div className="od-staff-wrap">
        <h1 className="od-board-title">Staff Dashboard</h1>
        <p className="error" style={{ marginTop: 16 }}>
          This dashboard is staff only. You are signed in as {user.name} (
          {user.role}). Staff roles are granted by an admin.
        </p>
      </div>
    );
  }

  const t = data?.totals;
  const bookingBySlot = new Map<number, Booking>();
  bookings
    .filter((b) => b.status === "booked")
    .forEach((b) => bookingBySlot.set(b.slot_id, b));

  return (
    <div className="od-staff-wrap">
      <StaffTabs active="times" />
      {error && (
        <p className="error" style={{ marginTop: 16 }}>
          {error}
        </p>
      )}

      {/* ------------------------- Open times ------------------------- */}
      <section className="od-board-grid">
        <div className="od-board-main">
          <h1>Open times</h1>
          <p className="lede" style={{ marginTop: 14 }}>
            These are the times students see under Talk to Dr. Roberts. A
            booked time cannot be removed, so nobody is left without a
            meeting.
          </p>
          <div className="od-list-rows" style={{ marginTop: 24 }}>
            {slots.map((s) => {
              const booking = bookingBySlot.get(s.id);
              const free = s.status === "open";
              return (
                <div className="od-times-row" key={s.id}>
                  <div className="row-main">
                    <div className="row-title">{slotDayLabel(s)}</div>
                    <div className="row-sub">
                      {free
                        ? `Open · ${s.type === "call" ? "Call" : "In person"}`
                        : booking
                          ? `Booked by ${booking.email}`
                          : "Booked"}
                    </div>
                  </div>
                  {free && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => deleteSlot(s.id)}
                    >
                      Remove
                    </button>
                  )}
                </div>
              );
            })}
          </div>
          {slots.length === 0 && (
            <p style={{ margin: "16px 0 0", color: "var(--secondary)" }}>
              No open times. Students see a note to email the office
              instead.
            </p>
          )}
        </div>

        <form className="od-board-aside" onSubmit={addSlot} noValidate>
          <h2 style={{ fontSize: 24 }}>Add a time</h2>
          <label className="od-field-label" htmlFor="od-slot-date">
            Day
          </label>
          <input
            id="od-slot-date"
            className="od-field"
            type="date"
            required
            value={slotForm.date}
            onChange={(e) =>
              setSlotForm({ ...slotForm, date: e.target.value })
            }
          />
          <label className="od-field-label" htmlFor="od-slot-start">
            Start time
          </label>
          <input
            id="od-slot-start"
            className="od-field"
            type="time"
            required
            value={slotForm.start_time}
            onChange={(e) =>
              setSlotForm({ ...slotForm, start_time: e.target.value })
            }
          />
          <label className="od-field-label" htmlFor="od-slot-end">
            End time
          </label>
          <input
            id="od-slot-end"
            className="od-field"
            type="time"
            required
            value={slotForm.end_time}
            onChange={(e) =>
              setSlotForm({ ...slotForm, end_time: e.target.value })
            }
          />
          <label className="od-field-label" htmlFor="od-slot-type">
            Type
          </label>
          <select
            id="od-slot-type"
            className="od-field"
            value={slotForm.type}
            onChange={(e) =>
              setSlotForm({ ...slotForm, type: e.target.value })
            }
          >
            <option value="call">Call</option>
            <option value="in-person">In person</option>
          </select>
          <div className="od-form-error" aria-live="polite">
            {slotError}
          </div>
          <button type="submit" className="od-send-btn">
            Add time
          </button>
        </form>
      </section>

      {/* --------------------------- Bookings -------------------------- */}
      <h2 style={{ marginTop: 56 }}>Bookings</h2>
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
                    <button
                      className="secondary"
                      onClick={() => cancelBooking(b.id)}
                    >
                      Cancel (re-opens slot)
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* --------------------------- Overview -------------------------- */}
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

      {/* ------------------------- Outreach log ------------------------ */}
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
