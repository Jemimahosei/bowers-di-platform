"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken, type User } from "../lib/api";

/* Open Door header, per mockups 01 (public) and 02 (staff).
 * Public: door logo + "Open Door", links Latest issue · Talk to
 * Dr. Roberts · Staff sign in.
 * Staff routes (/campaigns, /audiences, /dashboard): door logo +
 * "Open Door · Staff", "Signed in as …" and Sign out.
 * /login and /unsubscribe render no global header — those pages carry
 * their own centered logo column (mockups 04 and 05). */

const STAFF_ROUTES = ["/campaigns", "/audiences", "/dashboard"];
const BARE_ROUTES = ["/login", "/unsubscribe"];

export function DoorMark({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={Math.round(size * (26 / 22))}
      viewBox="0 0 22 26"
      aria-hidden="true"
    >
      <path d="M2 25V11a9 9 0 0 1 18 0v14z" fill="#b31b1b" />
      <path d="M11 25V8a6 6 0 0 1 6 6v11z" fill="#222222" />
    </svg>
  );
}

export default function Header() {
  const pathname = usePathname() ?? "/";
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
    window.addEventListener("opendoor-auth-changed", load);
    return () => window.removeEventListener("opendoor-auth-changed", load);
  }, []);

  function logout() {
    setToken(null);
    setUser(null);
  }

  if (BARE_ROUTES.some((r) => pathname.startsWith(r))) return null;

  if (STAFF_ROUTES.some((r) => pathname.startsWith(r))) {
    return (
      <header className="od-staff-header">
        <div className="od-staff-header-inner">
          <Link href="/" className="od-logo">
            <DoorMark size={20} />
            <span>Open Door</span>
            <span className="od-staff-word">Staff</span>
          </Link>
          <div className="od-signed-in">
            {user ? (
              <>
                <span className="who">Signed in as {user.email}</span>
                <button type="button" onClick={logout}>
                  Sign out
                </button>
              </>
            ) : (
              <Link href="/login">Staff sign in</Link>
            )}
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="od-header">
      <div className="od-header-inner">
        <Link href="/" className="od-logo">
          <DoorMark />
          <span>Open Door</span>
        </Link>
        <nav className="od-nav" aria-label="Main">
          <Link href="/#issue">Latest issue</Link>
          <Link href="/#talk">Talk to Dr. Roberts</Link>
          {user ? (
            <>
              <Link href="/campaigns">Staff board</Link>
              <button type="button" onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="od-nav-quiet">
              Staff sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
