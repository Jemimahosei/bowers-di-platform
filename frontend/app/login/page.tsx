"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, setToken } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.login(form);
      setToken(res.token);
      router.push("/dashboard");
    } catch {
      setError("Login failed. Check your email and password and try again.");
    }
  }

  return (
    <div className="container">
      <h1>Log in</h1>
      <p className="lede">
        Staff and students log in to access the staff dashboard.
      </p>
      {error && <p className="error">{error}</p>}
      <form className="form" onSubmit={submit}>
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
        <button type="submit">Log in</button>
      </form>
      <p>
        No account yet? <Link href="/register">Register as a student</Link>.
      </p>
    </div>
  );
}
