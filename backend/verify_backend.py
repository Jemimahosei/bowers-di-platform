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


def req_raw(path, token=None):
    """GET returning (status, raw text) — for non-JSON responses."""
    r = urllib.request.Request(BASE + path, method="GET")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def req_multipart(path, fields, files, token=None):
    """POST a multipart/form-data body (CSV uploads, org submissions).

    fields: {name: value}; files: {field: (filename, bytes, content-type)}.
    """
    boundary = "----bowers-test-boundary"
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for name, (filename, content, ctype) in files.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    data = b"".join(parts)
    r = urllib.request.Request(BASE + path, data=data, method="POST")
    r.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
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
    db_path = Path("/tmp/opendoor_verify.db")
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
        check("health reports email_mode console, no last error",
              body.get("email_mode") == "console"
              and body.get("last_email_error") == "",
              f"body={body}")

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

        # ---- Newsletter flow (Cornell domain only) ----
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Outsider", "email": "outsider@gmail.com",
            "interests": [], "topics": [], "source": "website"})
        check("non-Cornell signup -> 400 with Cornell message",
              status == 400 and "Cornell" in body.get("detail", ""),
              f"status={status} body={body}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Core Person", "email": "core@cornell.edu",
            "interests": [], "topics": [], "source": "website"})
        check("Cornell signup -> 201, subscribed at once, no token",
              status == 201 and body.get("ok") is True
              and "confirmation_token" not in body,
              f"status={status} body={body}")
        check("signup with no email configured -> email_sent False",
              body.get("email_sent") is False
              and body.get("email_configured") is False,
              f"body={body}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "News Person", "email": "news@cornell.edu",
            "interests": ["Tapia"], "topics": ["events"], "source": "website"})
        check("newsletter signup -> 201, subscribed at once",
              status == 201 and body.get("ok") is True
              and "confirmation_token" not in body,
              f"status={status} body={body}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "News Person", "email": "news@cornell.edu",
            "interests": [], "topics": [], "source": "website"})
        check("signup when subscribed -> already_subscribed",
              status == 200 and body.get("already_subscribed") is True,
              f"status={status} body={body}")
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Pending Person", "email": "pending@cornell.edu",
            "interests": [], "topics": [], "source": "tabling"})
        check("second signup -> 201", status == 201, f"status={status}")
        status, body = req("POST", "/api/newsletter/unsubscribe",
                           {"email": "news@cornell.edu"})
        check("unsubscribe -> ok", status == 200 and body.get("ok") is True)
        status, body = req("GET", "/api/newsletter/subscribers",
                           token=admin_token)
        subs = {s["email"]: s for s in body} if isinstance(body, list) else {}
        check("admin subscribers list",
              status == 200 and subs.get("news@cornell.edu", {}).get("status")
              == "unsubscribed"
              and subs.get("pending@cornell.edu", {}).get("status") == "confirmed"
              and subs.get("core@cornell.edu", {}).get("status") == "confirmed",
              f"status={status} body={body}")
        status, body = req("GET", "/api/newsletter/subscribers",
                           token=student_token)
        check("student subscribers -> 403", status == 403, f"status={status}")

        # ---- Core 1: audiences, contacts, CSV upload ----
        status, body = req("POST", "/api/audiences", {
            "name": "NSBE members", "source_org": "NSBE",
            "description": "Cornell NSBE chapter contacts"}, token=admin_token)
        check("admin POST audience -> 201",
              status == 201 and body.get("id"), f"status={status} body={body}")
        nsbe_id = body.get("id")
        status, body = req("POST", "/api/audiences", {
            "name": "Sneaky", "source_org": "NSBE"}, token=student_token)
        check("student POST audience -> 403", status == 403, f"status={status}")
        status, body = req("POST", f"/api/audiences/{nsbe_id}/contacts", {
            "name": "Manual Person", "email": "manual@test.demo",
            "source_org": "NSBE", "interests": ["Tapia", "Mentorship"],
            "tags": ["sophomore"]}, token=admin_token)
        check("admin manual add contact -> 201",
              status == 201 and body.get("email") == "manual@test.demo",
              f"status={status} body={body}")
        manual_id = body.get("id")
        status, body = req("POST", f"/api/audiences/{nsbe_id}/contacts", {
            "name": "Manual Person", "email": "manual@test.demo"},
            token=admin_token)
        check("duplicate contact in audience -> 409",
              status == 409, f"status={status}")
        status, body = req("POST", f"/api/audiences/{nsbe_id}/contacts", {
            "name": "Bad", "email": "not-an-email"}, token=admin_token)
        check("invalid contact email -> 400", status == 400, f"status={status}")
        status, text = req_raw("/api/audiences/contacts/template",
                               token=admin_token)
        check("CSV template",
              status == 200 and text.startswith("name,email,org,interests"),
              f"status={status} text={text!r}")
        csv_text = (
            "name,email,org,interests\n"
            "Csv One,csv1@test.demo,NSBE,Tapia; Mentorship\n"
            "Csv Two,csv2@test.demo,NSBE,Code Afrique\n"
            "Csv Three,csv3@test.demo,,Resources\n"
            "Bad Row,not-an-email,NSBE,Tapia\n"
        ).encode()
        status, body = req_multipart(
            f"/api/audiences/{nsbe_id}/contacts/upload",
            {"preview": "true"},
            {"file": ("contacts.csv", csv_text, "text/csv")},
            token=admin_token)
        check("CSV upload preview (3 valid, 1 invalid)",
              status == 200 and body.get("valid_rows") == 3
              and body.get("invalid_rows") == 1,
              f"status={status} body={body}")
        status, body = req_multipart(
            f"/api/audiences/{nsbe_id}/contacts/upload",
            {"preview": "false"},
            {"file": ("contacts.csv", csv_text, "text/csv")},
            token=admin_token)
        check("CSV upload import (3 imported, 1 skipped)",
              status == 200 and body.get("imported") == 3
              and body.get("skipped") == 1,
              f"status={status} body={body}")
        status, body = req_multipart(
            f"/api/audiences/{nsbe_id}/contacts/upload",
            {"preview": "false"},
            {"file": ("contacts.csv", csv_text, "text/csv")},
            token=admin_token)
        check("CSV re-upload imports 0 (all duplicates)",
              status == 200 and body.get("imported") == 0,
              f"status={status} body={body}")
        status, body = req("PATCH",
                           f"/api/audiences/{nsbe_id}/contacts/{manual_id}",
                           {"opted_out": True}, token=admin_token)
        check("opt-out a contact",
              status == 200 and body.get("opted_out") is True,
              f"status={status} body={body}")
        status, body = req("GET", f"/api/audiences/{nsbe_id}",
                           token=admin_token)
        check("audience detail counts (4 contacts, 1 opted out)",
              status == 200 and body.get("contact_count") == 4
              and body.get("opted_out_count") == 1
              and len(body.get("contacts", [])) == 4,
              f"status={status} body={body}")
        status, body = req("GET", "/api/audiences", token=student_token)
        check("student listing audiences -> 403", status == 403, f"status={status}")

        # ---- Org-rep submissions (public -> staff approval) ----
        status, body = req("POST", "/api/org-submissions", {
            "org_name": "URMC", "rep_name": "Rep Person",
            "rep_email": "rep@test.demo", "notes": "chapter list",
            "contacts": [
                {"name": "Urmc One", "email": "urmc1@test.demo",
                 "interests": ["Tapia"]},
                {"name": "Urmc Two", "email": "urmc2@test.demo",
                 "interests": []},
            ]})
        check("org submission (public) -> 201 pending",
              status == 201 and body.get("status") == "pending"
              and len(body.get("contacts", [])) == 2,
              f"status={status} body={body}")
        sub_id = body.get("id")
        status, body = req("POST", "/api/org-submissions", {
            "org_name": "", "rep_name": "X", "rep_email": "x@test.demo",
            "contacts": [{"name": "A", "email": "a@test.demo"}]})
        check("org submission without org name -> 400",
              status == 400, f"status={status}")
        status, body = req("POST", "/api/org-submissions", {
            "org_name": "URMC", "rep_name": "X", "rep_email": "x@test.demo",
            "contacts": []})
        check("org submission with no valid contacts -> 400",
              status == 400, f"status={status}")
        status, body = req("GET", "/api/org-submissions", token=admin_token)
        check("admin lists org submissions",
              status == 200 and len(body) == 1
              and body[0].get("status") == "pending",
              f"status={status} body={body}")
        status, body = req("POST", f"/api/org-submissions/{sub_id}/review",
                           {"decision": "approve"}, token=admin_token)
        check("approve org submission -> contacts added to new audience",
              status == 200 and body.get("status") == "approved"
              and body.get("contacts_added") == 2
              and body.get("audience_id"),
              f"status={status} body={body}")
        urmc_audience_id = body.get("audience_id")
        status, body = req("POST", f"/api/org-submissions/{sub_id}/review",
                           {"decision": "approve"}, token=admin_token)
        check("re-review approved submission -> 409",
              status == 409, f"status={status}")
        status, body = req("POST", "/api/org-submissions", {
            "org_name": "NSBE", "rep_name": "R2",
            "rep_email": "r2@test.demo",
            "contacts": [{"name": "B", "email": "b@test.demo"}]})
        sub2_id = body.get("id")
        status, body = req("POST", f"/api/org-submissions/{sub2_id}/review",
                           {"decision": "reject"}, token=admin_token)
        check("reject org submission",
              status == 200 and body.get("status") == "rejected",
              f"status={status} body={body}")

        # ---- Core 2: campaigns (no SMTP configured in this VM) ----
        status, body = req("POST", "/api/campaigns", {
            "subject": "No audience", "body": "hello"}, token=admin_token)
        check("campaign with no audience/org -> 400",
              status == 400, f"status={status}")
        status, body = req("POST", "/api/campaigns", {
            "subject": "Bad audience", "body": "hello",
            "audience_ids": [99999]}, token=admin_token)
        check("campaign with unknown audience -> 404",
              status == 404, f"status={status}")
        status, body = req("POST", "/api/campaigns", {
            "subject": "Tapia update", "body": "Tapia news for members",
            "sender_name": "Center for Belonging",
            "audience_ids": [nsbe_id],
            "interest_filter": "Tapia"}, token=admin_token)
        check("campaign draft -> 201, recipient count excludes opted-out",
              status == 201 and body.get("status") == "draft"
              and body.get("recipient_count") == 1,
              f"status={status} body={body}")
        campaign_id = body.get("id")
        status, body = req("GET", f"/api/campaigns/{campaign_id}",
                           token=admin_token)
        check("campaign detail lists the 1 matching recipient",
              status == 200 and len(body.get("recipients", [])) == 1
              and body["recipients"][0]["email"] == "csv1@test.demo",
              f"status={status} body={body}")
        status, body = req("PATCH", f"/api/campaigns/{campaign_id}",
                           {"subject": "Tapia update (edited)"},
                           token=admin_token)
        check("edit draft campaign",
              status == 200 and body.get("subject") == "Tapia update (edited)",
              f"status={status} body={body}")
        status, body = req("POST", f"/api/campaigns/{campaign_id}/send",
                           {}, token=admin_token)
        check("send with no email configured -> queued, never claimed sent",
              status == 200 and body.get("status") == "queued"
              and body.get("email_configured") is False
              and body.get("recipient_count") == 1,
              f"status={status} body={body}")
        status, body = req("GET", f"/api/campaigns/{campaign_id}",
                           token=admin_token)
        check("queued campaign recipients stored as queued, not sent",
              status == 200
              and all(r["status"] == "queued"
                      for r in body.get("recipients", []))
              and len(body.get("recipients", [])) == 1,
              f"status={status} body={body}")
        status, body = req("PATCH", f"/api/campaigns/{campaign_id}",
                           {"subject": "too late"}, token=admin_token)
        check("edit queued campaign -> 409", status == 409, f"status={status}")
        # ---- Newsletter issues: built from the real resources ----
        status, all_resources = req("GET", "/api/resources")
        check("resources list for issue picker (26)",
              status == 200 and len(all_resources) == 26,
              f"got {len(all_resources) if isinstance(all_resources, list) else all_resources}")
        res1, res2 = all_resources[0], all_resources[1]
        status, body = req("POST", "/api/campaigns", {
            "subject": "Issue: resources for members",
            "body": "Here are two resources from the Center.",
            "sender_name": "Center for Belonging",
            "resource_ids": [res1["id"], res2["id"]],
            "audience_ids": [nsbe_id]}, token=admin_token)
        check("issue compose with 2 real resources -> 201, preview lists them",
              status == 201
              and len(body.get("featured_resources", [])) == 2
              and [r["title"] for r in body["featured_resources"]]
              == [res1["title"], res2["title"]]
              and body.get("recipient_count") == 3,
              f"status={status} body={body}")
        issue_id = body.get("id")
        status, body = req("GET", f"/api/campaigns/{issue_id}",
                           token=admin_token)
        check("issue detail preview includes featured resources + count",
              status == 200
              and len(body.get("featured_resources", [])) == 2
              and body.get("recipient_count") == 3,
              f"status={status} body={body}")
        status, body = req("POST", "/api/campaigns", {
            "subject": "Bad resource", "body": "hello",
            "resource_ids": [99999], "audience_ids": [nsbe_id]},
            token=admin_token)
        check("issue with unknown resource -> 404",
              status == 404, f"status={status}")
        status, body = req("POST", f"/api/campaigns/{issue_id}/send",
                           {}, token=admin_token)
        check("issue send with no email configured -> queued, never claimed sent",
              status == 200 and body.get("status") == "queued"
              and body.get("email_configured") is False
              and body.get("recipient_count") == 3
              and len(body.get("featured_resources", [])) == 2,
              f"status={status} body={body}")
        status, body = req("GET", f"/api/campaigns/{issue_id}",
                           token=admin_token)
        check("queued issue recipients stored as queued, not sent",
              status == 200
              and all(r["status"] == "queued"
                      for r in body.get("recipients", []))
              and len(body.get("recipients", [])) == 3,
              f"status={status} body={body}")
        # A confirmed self-signup subscriber is pulled in when requested.
        status, body = req("POST", "/api/newsletter/signup", {
            "name": "Confirmed Person", "email": "confirm@cornell.edu",
            "interests": [], "topics": [], "source": "website"})
        status, body = req("POST", "/api/campaigns", {
            "subject": "All members", "body": "hello everyone",
            "audience_ids": [nsbe_id, urmc_audience_id],
            "include_self_signup": True}, token=admin_token)
        check("campaign incl. self-signup counts 5 contacts + 3 subscribers",
              status == 201 and body.get("recipient_count") == 8,
              f"status={status} body={body}")
        # An issue can go to newsletter subscribers alone — no audience.
        status, body = req("POST", "/api/campaigns", {
            "subject": "Subscribers only", "body": "for the list",
            "include_self_signup": True}, token=admin_token)
        check("subscribers-only issue -> 201, 3 confirmed subscribers",
              status == 201 and body.get("recipient_count") == 3,
              f"status={status} body={body}")
        subs_only_id = body.get("id")
        status, body = req("PATCH", f"/api/campaigns/{subs_only_id}",
                           {"resource_ids": [res1["id"]]},
                           token=admin_token)
        check("edit draft issue resources",
              status == 200
              and len(body.get("featured_resources", [])) == 1
              and body["featured_resources"][0]["title"] == res1["title"],
              f"status={status} body={body}")

        # ---- Core 3: slot-based booking with Dr. Roberts ----
        status, body = req("POST", "/api/slots", {
            "date": "2027-01-15", "start_time": "14:00",
            "end_time": "14:30", "type": "call"}, token=admin_token)
        check("admin creates slot -> 201 open",
              status == 201 and body.get("status") == "open"
              and body.get("host") == "Dr. LeeAnn Roberts",
              f"status={status} body={body}")
        slot_a = body.get("id")
        status, body = req("POST", "/api/slots", {
            "date": "2027-01-15", "start_time": "15:00",
            "end_time": "14:30", "type": "call"}, token=admin_token)
        check("slot end before start -> 400", status == 400, f"status={status}")
        status, body = req("POST", "/api/slots", {
            "date": "2027-01-15", "start_time": "16:00",
            "end_time": "16:30", "type": "in-person"}, token=student_token)
        check("student creates slot -> 403", status == 403, f"status={status}")
        status, body = req("GET", "/api/slots")
        check("public lists open slots",
              status == 200 and len(body) == 1
              and body[0]["id"] == slot_a,
              f"status={status} body={body}")
        status, body = req("POST", f"/api/slots/{slot_a}/book", {
            "name": "Visitor", "email": "visitor@test.demo",
            "purpose": "advising"})
        check("book with non-Cornell email -> 400",
              status == 400, f"status={status}")
        status, body = req("POST", f"/api/slots/{slot_a}/book", {
            "name": "Visitor Person", "email": "vp123@cornell.edu",
            "purpose": "conference support"})
        check("book open slot -> 201 booked",
              status == 201 and body.get("status") == "booked"
              and body.get("slot", {}).get("status") == "booked",
              f"status={status} body={body}")
        booking_a = body.get("id")
        status, body = req("GET", "/api/slots")
        check("booked slot no longer listed as open",
              status == 200 and len(body) == 0, f"status={status} body={body}")
        status, body = req("POST", f"/api/slots/{slot_a}/book", {
            "name": "Second", "email": "second@cornell.edu",
            "purpose": "x"})
        check("double-book a booked slot -> 409",
              status == 409, f"status={status}")
        status, body = req("GET", "/api/bookings", token=student_token)
        check("student listing bookings -> 403", status == 403, f"status={status}")
        status, body = req("GET", "/api/bookings", token=admin_token)
        check("admin lists bookings",
              status == 200 and len(body) == 1
              and body[0]["id"] == booking_a,
              f"status={status} body={body}")
        status, body = req("POST", f"/api/bookings/{booking_a}/cancel",
                           {}, token=admin_token)
        check("admin cancels booking -> slot re-opens",
              status == 200 and body.get("status") == "cancelled"
              and body.get("slot", {}).get("status") == "open",
              f"status={status} body={body}")
        status, body = req("POST", f"/api/bookings/{booking_a}/cancel",
                           {}, token=admin_token)
        check("cancel already-cancelled booking -> 409",
              status == 409, f"status={status}")
        status, body = req("DELETE", f"/api/slots/{slot_a}",
                           token=admin_token)
        check("delete re-opened slot -> 200",
              status == 200 and body.get("ok") is True,
              f"status={status} body={body}")
        status, body = req("POST", "/api/slots", {
            "date": "2027-01-15", "start_time": "10:00",
            "end_time": "10:30", "type": "in-person"}, token=admin_token)
        slot_b = body.get("id")
        status, body = req("POST", f"/api/slots/{slot_b}/book", {
            "name": "Keeper", "email": "keeper@cornell.edu",
            "purpose": "mentorship"})
        check("book second slot (stays booked)",
              status == 201 and body.get("status") == "booked",
              f"status={status} body={body}")
        status, body = req("DELETE", f"/api/slots/{slot_b}",
                           token=admin_token)
        check("delete booked slot -> 409", status == 409, f"status={status}")

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
              status == 200 and totals.get("subscribers") == 4
              and totals.get("confirmed_subscribers") == 3
              and totals.get("audiences") == 2
              and totals.get("contacts") == 6
              and totals.get("opted_out_contacts") == 1
              and totals.get("campaigns") == 4
              and totals.get("campaigns_sent") == 0
              and totals.get("open_slots") == 0
              and totals.get("upcoming_bookings") == 1
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
        check("dashboard bookings_by_status (1 booked, 1 cancelled)",
              body.get("bookings_by_status") == {"booked": 1, "cancelled": 1},
              f"body={body.get('bookings_by_status')}")
        check("dashboard slots_by_status (0 open, 1 booked)",
              body.get("slots_by_status") == {"open": 0, "booked": 1},
              f"body={body.get('slots_by_status')}")
        check("dashboard campaigns_by_status (2 draft, 2 queued)",
              body.get("campaigns_by_status") == {
                  "draft": 2, "queued": 2, "sent": 0, "partially_sent": 0},
              f"body={body.get('campaigns_by_status')}")
        status, body = req("GET", "/api/reports/summary", token=admin_token)
        check("reports summary (admin)",
              status == 200 and body.get("totals", {}).get("outreach_contacts") == 40
              and body.get("open_bookings", {}).get("count") == 1
              and len(body.get("audiences", [])) == 2
              and len(body.get("campaigns", [])) == 4,
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
