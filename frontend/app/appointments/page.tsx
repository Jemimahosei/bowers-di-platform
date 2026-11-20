"use client";

import { useEffect, useState } from "react";
import { api, type Slot } from "../../lib/api";

export default function AppointmentsPage() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState<Slot | null>(null);
  const [form, setForm] = useState({ name: "", email: "", purpose: "" });
  const [booked, setBooked] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .slots(true)
      .then((list) => {
        setSlots(list);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not reach the API — slots are unavailable right now.");
        setLoading(false);
      });
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!picked) return;
    setError("");
    try {
      await api.bookSlot(picked.id, {
        name: form.name,
        email: form.email,
        purpose: form.purpose,
      });
      setBooked(true);
      setSlots((prev) => prev.filter((s) => s.id !== picked.id));
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("400")
          ? "A Cornell email address is required to book."
          : err instanceof Error && err.message.includes("409")
          ? "That slot was just taken. Pick another one."
          : "Could not book that slot. Try again."
      );
    }
  }

  return (
    <div className="container">
      <h1>Book an Appointment</h1>
      <p className="lede">
        Book a call or an in-person appointment with Dr. LeeAnn Roberts,
        Director of the DEIB office. Pick an open time — it&apos;s yours
        once you book it.
      </p>
      <p className="notice">
        Questions? Email the office at{" "}
        <a href="mailto:deib-office@bowers.cornell.edu">
          deib-office@bowers.cornell.edu
        </a>
        .
      </p>
      {error && <p className="error">{error}</p>}

      {booked && picked ? (
        <div className="success">
          <h3 style={{ marginTop: 0 }}>Booked</h3>
          <p>
            Thank you, {form.name}. Your appointment with {picked.host} is
            booked for {picked.date}, {picked.start_time}–{picked.end_time} (
            {picked.type}). A confirmation is on its way to {form.email}.
          </p>
          <p>
            Need to change it? Email{" "}
            <a href="mailto:deib-office@bowers.cornell.edu">
              deib-office@bowers.cornell.edu
            </a>
            .
          </p>
        </div>
      ) : (
        <>
          <h2>Open times</h2>
          {loading ? (
            <p>Loading…</p>
          ) : slots.length === 0 ? (
            <p>
              No open times right now. Dr. Roberts adds her availability
              here — check back soon, or email{" "}
              <a href="mailto:deib-office@bowers.cornell.edu">
                deib-office@bowers.cornell.edu
              </a>{" "}
              to ask.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Type</th>
                  <th>With</th>
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
                    <td>
                      <button
                        className={picked?.id === s.id ? undefined : "secondary"}
                        onClick={() => setPicked(s)}
                      >
                        {picked?.id === s.id ? "Selected" : "Select"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {picked && (
            <form className="form" onSubmit={submit}>
              <h3 style={{ margin: 0 }}>
                Book {picked.date}, {picked.start_time}–{picked.end_time} (
                {picked.type})
              </h3>
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
              </label>
              <label>
                What would you like to talk about?
                <input
                  required
                  value={form.purpose}
                  onChange={(e) =>
                    setForm({ ...form, purpose: e.target.value })
                  }
                  placeholder="e.g. conference support, resources, advising"
                />
              </label>
              <button type="submit">Book this time</button>
            </form>
          )}
        </>
      )}
    </div>
  );
}
