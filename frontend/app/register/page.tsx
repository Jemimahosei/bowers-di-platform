"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, setToken } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.register(form);
      setToken(res.token);
      router.push("/");
    } catch {
      setError("Registration failed. That email may already be registered.");
    }
  }

  return (
    <div className="container">
      <h1>Register</h1>
      <p className="lede">Create a student account for the platform.</p>
      <p className="notice">
        New accounts are students. Staff roles are granted by an admin.
      </p>
      {error && <p className="error">{error}</p>}
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
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        <button type="submit">Register</button>
      </form>
      <p>
        Already have an account? <Link href="/login">Log in</Link>.
      </p>
    </div>
  );
}
