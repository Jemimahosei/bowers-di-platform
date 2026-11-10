"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getToken, setToken, type User } from "../lib/api";

export default function Header() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const load = () => {
      if (!getToken()) {
        setUser(null);
        return;
      }
      api
        .me()
        .then(setUser)
        .catch(() => setUser(null));
    };
    load();
    window.addEventListener("bowers-auth-changed", load);
    return () => window.removeEventListener("bowers-auth-changed", load);
  }, []);

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <nav className="nav">
      <Link href="/" className="brand">
        Belonging at Bowers
      </Link>
      <Link href="/resources">Resources</Link>
      <Link href="/conferences">Conferences</Link>
      <Link href="/programs">Programs</Link>
      <Link href="/newsletter">Newsletter</Link>
      <Link href="/appointments">Book an Appointment</Link>
      <Link href="/dashboard">Staff Dashboard</Link>
      {user ? (
        <span className="user">
          {user.name} ({user.role})
          <button onClick={logout}>Log out</button>
        </span>
      ) : (
        <>
          <Link href="/login">Log in</Link>
          <Link href="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
