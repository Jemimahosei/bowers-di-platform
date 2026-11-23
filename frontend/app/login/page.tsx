"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, setToken } from "../../lib/api";
import { DoorMark } from "../../components/Header";

/* Staff sign in — mockup 04. Centered 400px column, own logo (the
 * global header is suppressed on this route). Subscribers never need
 * an account; this is staff only. On success the existing flow goes
 * to the staff dashboard. */

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [signingIn, setSigningIn] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("Enter your email.");
      return;
    }
    if (!password) {
      setError("Enter your password.");
      return;
    }
    setSigningIn(true);
    try {
      const res = await api.login({ email: email.trim(), password });
      setToken(res.token);
      router.push("/dashboard");
    } catch {
      setError("Login failed. Check your email and password and try again.");
      setSigningIn(false);
    }
  }

  return (
    <div className="od-auth-wrap">
      <div className="od-auth-col">
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            minHeight: 44,
            textDecoration: "none",
            fontWeight: 700,
            fontSize: 20,
            lineHeight: 1.1,
            color: "var(--text)",
          }}
        >
          <DoorMark size={20} />
          Open Door
        </Link>
        <h1>Staff sign in</h1>
        <p className="od-auth-sub">
          For Center for Belonging staff only. Subscribers never need an
          account.
        </p>
        <form onSubmit={submit} noValidate>
          <label htmlFor="od-login-email">Cornell email</label>
          <input
            id="od-login-email"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError("");
            }}
            autoComplete="email"
          />
          <label htmlFor="od-login-password" className="tight">
            Password
          </label>
          <input
            id="od-login-password"
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setError("");
            }}
            autoComplete="current-password"
          />
          <div className="od-auth-error" aria-live="polite">
            {error}
          </div>
          <button
            type="submit"
            className="od-auth-submit"
            disabled={signingIn}
          >
            {signingIn ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
