"use client";

import { useState } from "react";
import { api } from "../../lib/api";

export default function AppointmentsPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    topic: "",
    preferred_date: "",
    preferred_time: "",
    notes: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.requestAppointment({
        name: form.name,
        email: form.email,
        topic: form.topic,
        preferred_date: form.preferred_date || undefined,
        preferred_time: form.preferred_time || undefined,
        notes: form.notes || undefined,
      });
      setSubmitted(true);
    } catch {
      setError("Could not send that request. Check the API and try again.");
    }
  }

  return (
    <div className="container">
      <h1>Book an Appointment</h1>
      <p className="lede">
        Book an appointment or call with Dr. LeeAnn Roberts, Director of the
        DEIB office.
      </p>
      <p className="notice">
        Requests go to the office (
        <a href="mailto:deib-office@bowers.cornell.edu">
          deib-office@bowers.cornell.edu
        </a>
        ) for confirmation. No calendar times are shown here because
        availability is confirmed by the office.
      </p>
      {error && <p className="error">{error}</p>}
      {submitted ? (
        <div className="success">
          <h3 style={{ marginTop: 0 }}>Request received</h3>
          <p>
            Thank you, {form.name}. Your appointment request has been sent to
            the DEIB office. The office will confirm a time with you at{" "}
            {form.email}.
          </p>
        </div>
      ) : (
        <form className="form" onSubmit={submit}>
          <label>
            Name
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="netid@cornell.edu"
            />
          </label>
          <label>
            Topic
            <span>What would you like to talk about?</span>
            <input
              required
              value={form.topic}
              onChange={(e) => setForm({ ...form, topic: e.target.value })}
              placeholder="e.g. conference support, resources, advising"
            />
          </label>
          <label>
            Preferred date
            <input
              type="date"
              value={form.preferred_date}
              onChange={(e) =>
                setForm({ ...form, preferred_date: e.target.value })
              }
            />
          </label>
          <label>
            Preferred time
            <input
              type="time"
              value={form.preferred_time}
              onChange={(e) =>
                setForm({ ...form, preferred_time: e.target.value })
              }
            />
          </label>
          <label>
            Notes
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Anything the office should know before the appointment"
            />
          </label>
          <button type="submit">Request appointment</button>
        </form>
      )}
    </div>
  );
}
