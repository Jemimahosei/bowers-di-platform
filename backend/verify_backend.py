"""End-to-end verification for the Bowers backend.

Stdlib only. Starts uvicorn on a throwaway SQLite DB, curl-checks every
endpoint family, and prints PASS/FAIL per check. Usage:

    python3 verify_backend.py

Requires the venv deps installed (see requirements.txt).
Exits non-zero if any check fails.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def main():
    db_path = Path("/tmp/bowers_verify.db")
    if db_path.exists():
        db_path.unlink()
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["PYTHONPATH"] = str(BACKEND_DIR)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(BACKEND_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # Wait for health.
        up = False
        for _ in range(50):
            status, body = req("GET", "/api/health")
            if status == 200 and body.get("status") == "ok":
                up = True
                break
            time.sleep(0.2)
        check("health", up)
        if not up:
            return 1

        # ---- Seed correctness ----
        status, resources = req("GET", "/api/resources")
        check("resources seeded (25)", status == 200 and len(resources) == 25,
              f"got {len(resources)}")
        check("no example.org links in seed",
              all("example.org" not in (r.get("link") or "") for r in resources))
        status, office = req("GET", "/api/resources?category=Office%20services")
        check("office services = 4", len(office) == 4, f"got {len(office)}")
        status, found = req("GET", "/api/resources?search=Advising")
        check("resource search 'Advising'",
              status == 200 and len(found) == 1 and found[0]["title"] == "Advising")
        status, confs = req("GET", "/api/conferences")
        check("conferences seeded (5)", status == 200 and len(confs) == 5,
              f"got {len(confs)}")
        by_name = {c["name"]: c for c in confs}
        ghc = by_name.get("Grace Hopper Celebration 2026", {})
        check("GHC 2026 status=cancelled",
              ghc.get("status") == "cancelled", f"got {ghc.get('status')}")
        check("GHC 2026 date is 2026-10-27", ghc.get("date") == "2026-10-27")
        check("Tapia 2027 tba, date null",
              by_name.get("Tapia 2027", {}).get("status") == "tba"
              and by_name.get("Tapia 2027", {}).get("date") is None)
        check("Tapia 2026 past, 2026-09-16..18",
              by_name.get("Tapia 2026", {}).get("status") == "past"
              and by_name.get("Tapia 2026", {}).get("date") == "2026-09-16"
              and by_name.get("Tapia 2026", {}).get("end_date") == "2026-09-18")
        check("Code Afrique 2026 past, 146 students in description",
              "146 high school students" in by_name.get("Code Afrique 2026", {})
              .get("description", ""))
        status, upcoming = req("GET", "/api/conferences?upcoming=true")
        check("upcoming filter never includes GHC 2026",
              status == 200 and len(upcoming) == 1
              and upcoming[0]["name"] == "GHC India",
              f"got {[c['name'] for c in upcoming]}")
        status, events = req("GET", "/api/events")
        check("events seeded (10)", status == 200 and len(events) == 10,
              f"got {len(events)}")
        check("no invented event dates (all null)",
              all(e.get("date") is None for e in events))
        check("alumni dinner venue kept as jem said it",
              any(e["name"] == "Cornell alumni dinner"
                  and e.get("location") == "Baytech building" for e in events))

        # ---- Auth ----
        status, body = req("POST", "/api/auth/register", {
            "name": "Test Student", "email": "student@test.demo",
            "password": "password123"})
        check("register student -> 201 + role student",
              status == 201 and body.get("user", {}).get("role") == "student",
              f"status={status}")
        student_token = body.get("token")
        student_id = body.get("user", {}).get("id")
        status, body = req("POST", "/api/auth/register", {
            "name": "Sneaky", "email": "sneaky@test.demo",
            "password": "password123", "role": "admin"})
        check("register requesting admin -> 400",
              status == 400, f"status={status}")
        status, body = req("POST", "/api/auth/login", {
            "email": "student@test.demo", "password": "password123"})
        check("login ok", status == 200 and bool(body.get("token")))
        status, body = req("POST", "/api/auth/login", {
            "email": "student@test.demo", "password": "wrongpass"})
        check("login wrong password -> 401", status == 401, f"status={status}")
        status, body = req("GET", "/api/auth/me", token=student_token)
        check("me returns student",
              status == 200 and body.get("email") == "student@test.demo")
        status, body = req("GET", "/api/auth/me")
        check("me without token -> 401", status == 401, f"status={status}")
        status, body = req("POST", "/api/auth/login", {
            "email": "admin@center.demo", "password": "demo1234"})
        check("demo admin login", status == 200
              and body.get("user", {}).get("role") == "admin", f"status={status}")
        admin_token = body.get("token")
        status, body = req("GET", "/api/auth/users", token=admin_token)
        check("admin lists users",
              status == 200 and len(body) >= 2, f"got {len(body) if isinstance(body, list) else body}")
        status, body = req("GET", "/api/auth/users", token=student_token)
        check("student listing users -> 403", status == 403, f"status={status}")
        status, body = req("PATCH", f"/api/auth/users/{student_id}/role",
                           {"role": "faculty"}, token=admin_token)
        check("admin promotes student -> faculty",
              status == 200 and body.get("role") == "faculty", f"status={status}")
        status, body = req("PATCH", f"/api/auth/users/{student_id}/role",
                           {"role": "superuser"}, token=admin_token)
        check("invalid role -> 422", status == 422, f"status={status}")
        # Demote back so later role checks treat them as a student.
        req("PATCH", f"/api/auth/users/{student_id}/role",
            {"role": "student"}, token=admin_token)

        # ---- Role enforcement on writes ----
        status, body = req("POST", "/api/resources", {
            "title": "X", "description": "x", "category": "c",
            "audience": "a", "link": ""}, token=student_token)
        check("student POST resource -> 403", status == 403, f"status={status}")
        status, body = req("POST", "/api/resources", {
            "title": "X", "description": "x", "category": "c",
            "audience": "a", "link": ""})
        check("anonymous POST resource -> 401", status == 401, f"status={status}")
        status, body = req("GET", "/api/dashboard")
        check("anonymous dashboard -> 401", status == 401, f"status={status}")
        status, body = req("GET", "/api/dashboard", token=student_token)
        check("student dashboard -> 403", status == 403, f"status={status}")
        status, body = req("POST", "/api/resources", {
            "title": "Admin-added resource", "description": "added by test",
            "category": "Office services", "audience": "All students",
            "link": ""}, token=admin_token)
        check("admin POST resource -> 201",
              status == 201 and body.get("id"), f"status={status}")

        # ---- Participation ----
        tapia_id = by_name["Tapia 2026"]["id"]
        status, body = req("POST",
                           f"/api/conferences/{tapia_id}/participation",
                           {"note": "attended"}, token=student_token)
        check("student records own participation -> 201",
              status == 201 and body.get("user_id") == student_id,
              f"status={status} body={body}")
        status, body = req("POST",
                           f"/api/conferences/{tapia_id}/participation",
                           {"user_id": student_id, "note": "for someone else"},
                           token=student_token)
        check("student recording for another user -> 403",
              status == 403, f"status={status}")
        status, body = req("GET",
                           f"/api/conferences/{tapia_id}/participation",
                           token=admin_token)
        check("admin lists participation",
              status == 200 and len(body) == 1, f"got {len(body)}")
        status, body = req("GET",
                           f"/api/conferences/{tapia_id}/participation",
                           token=student_token)
        check("student listing participation -> 403",
              status == 403, f"status={status}")

        # ---- Newsletter flow ----
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "News Person", "email": "news@test.demo",
            "interests": ["Tapia"], "topics": ["events"], "source": "website"})
        check("newsletter signup -> 201 + token + url",
              status == 201 and body.get("confirmation_token")
              and body.get("confirmation_url", "").endswith(
                  body.get("confirmation_token", "")),
              f"status={status} body={body}")
        token1 = body.get("confirmation_token")
        status, body = req("GET",
                           f"/api/newsletter/confirm?token={token1}")
        check("newsletter confirm -> ok + email",
              status == 200 and body.get("email") == "news@test.demo",
              f"status={status} body={body}")
        status, body = req("GET",
                           f"/api/newsletter/confirm?token={token1}")
        check("confirm reuse -> 400", status == 400, f"status={status}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "News Person", "email": "news@test.demo",
            "interests": [], "topics": [], "source": "website"})
        check("signup when confirmed -> already_subscribed",
              status == 200 and body.get("already_subscribed") is True,
              f"status={status} body={body}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Pending Person", "email": "pending@test.demo",
            "interests": [], "topics": [], "source": "tabling"})
        check("second signup -> 201", status == 201, f"status={status}")
        token2 = body.get("confirmation_token")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Pending Person", "email": "pending@test.demo",
            "interests": [], "topics": [], "source": "tabling"})
        check("pending re-signup re-issues token",
              status == 200 and body.get("confirmation_token")
              and body.get("confirmation_token") != token2,
              f"status={status} body={body}")
        status, body = req("POST", "/api/newsletter/unsubscribe",
                           {"email": "news@test.demo"})
        check("unsubscribe -> ok", status == 200 and body.get("ok") is True)
        status, body = req("GET", "/api/newsletter/subscribers",
                           token=admin_token)
        subs = {s["email"]: s for s in body} if isinstance(body, list) else {}
        check("admin subscribers list",
              status == 200 and subs.get("news@test.demo", {}).get("status")
              == "unsubscribed"
              and subs.get("pending@test.demo", {}).get("status") == "pending",
              f"status={status} body={body}")
        status, body = req("GET", "/api/newsletter/subscribers",
                           token=student_token)
        check("student subscribers -> 403", status == 403, f"status={status}")

        # ---- Appointments ----
        status, body = req("POST", "/api/appointments", {
            "name": "Appt Person", "email": "appt@test.demo",
            "topic": "DEIB advising", "preferred_date": "2026-11-10",
            "preferred_time": "14:00", "notes": "first meeting"})
        check("appointment submit (public) -> 201 pending",
              status == 201 and body.get("status") == "pending"
              and body.get("id"), f"status={status} body={body}")
        appt_id = body.get("id")
        status, body = req("GET", "/api/appointments", token=student_token)
        check("student listing appointments -> 403",
              status == 403, f"status={status}")
        status, body = req("GET", "/api/appointments", token=admin_token)
        check("admin lists appointments",
              status == 200 and any(a["id"] == appt_id for a in body),
              f"status={status}")
        status, body = req("PATCH", f"/api/appointments/{appt_id}",
                           {"status": "confirmed"}, token=admin_token)
        check("admin confirms appointment",
              status == 200 and body.get("status") == "confirmed",
              f"status={status} body={body}")
        status, body = req("PATCH", f"/api/appointments/{appt_id}",
                           {"status": "banana"}, token=admin_token)
        check("invalid appointment status -> 422",
              status == 422, f"status={status}")

        # ---- Outreach (admin only, real rows) ----
        status, body = req("POST", "/api/outreach", {
            "date": "2026-11-06", "program": "NSBE tabling",
            "channel": "CampusGroups", "audience": "NSBE members",
            "contacts_reached": 40, "subject": "Center resources",
            "notes": "test entry"}, token=admin_token)
        check("admin POST outreach -> 201",
              status == 201 and body.get("contacts_reached") == 40,
              f"status={status} body={body}")
        status, body = req("GET", "/api/outreach", token=student_token)
        check("student listing outreach -> 403", status == 403, f"status={status}")
        status, body = req("GET", "/api/outreach/stats", token=admin_token)
        check("outreach stats from real rows",
              status == 200 and body.get("total_contacts") == 40
              and body.get("total_entries") == 1, f"body={body}")

        # ---- Dashboard / reports (computed from real rows only) ----
        status, body = req("GET", "/api/dashboard", token=admin_token)
        totals = body.get("totals", {}) if isinstance(body, dict) else {}
        check("dashboard totals reflect real rows",
              status == 200 and totals.get("subscribers") == 2
              and totals.get("confirmed_subscribers") == 0
              and totals.get("appointments_pending") == 0
              and totals.get("resources") == 26
              and totals.get("conferences") == 5
              and totals.get("events") == 10
              and totals.get("participation_total") == 1
              and totals.get("outreach_contacts") == 40,
              f"totals={totals}")
        pb = {r["conference"]: r["count"]
              for r in body.get("participation_by_conference", [])}
        check("dashboard participation_by_conference",
              pb.get("Tapia 2026") == 1 and pb.get("GHC India") == 0,
              f"pb={pb}")
        check("dashboard outreach_by_month has 2026-11",
              any(r["month"] == "2026-11" and r["contacts"] == 40
                  for r in body.get("outreach_by_month", [])),
              f"body={body.get('outreach_by_month')}")
        check("dashboard appointments_by_status has all 4 keys",
              set(body.get("appointments_by_status", {}).keys())
              == {"pending", "confirmed", "declined", "completed"}
              and body["appointments_by_status"].get("confirmed") == 1,
              f"body={body.get('appointments_by_status')}")
        status, body = req("GET", "/api/reports/summary", token=admin_token)
        check("reports summary (admin)",
              status == 200 and body.get("totals", {}).get("outreach_contacts") == 40
              and body.get("open_appointments", {}).get("count") == 0,
              f"status={status}")
        status, body = req("GET", "/api/reports/summary", token=student_token)
        check("reports summary student -> 403", status == 403, f"status={status}")

        # ---- Events create (admin) ----
        status, body = req("POST", "/api/events", {
            "name": "Test workshop", "description": "test",
            "category": "workshop"}, token=admin_token)
        check("admin POST event -> 201", status == 201, f"status={status}")
        status, body = req("POST", "/api/events", {
            "name": "Bad", "description": "x", "category": "party"},
            token=admin_token)
        check("invalid event category -> 422", status == 422, f"status={status}")

        failed = [r for r in RESULTS if not r[1]]
        print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed.")
        if failed:
            print("FAILED:")
            for name, _, detail in failed:
                print(f"  - {name} {detail}")
        return 1 if failed else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
