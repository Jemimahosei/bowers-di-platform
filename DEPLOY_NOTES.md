# Bowers D&I Platform — Deploy Notes

Backend rebuilt Nov 6, 2026 to the real spec (`REAL-SPEC.md`). Nothing was
pushed; no live service was touched.

## Newsletter as the core (Nov 20, 2026) — the reach reframe

jem: the newsletter should be the core feature, because it sends the
resources to students at the Cornell domain. Reframed around that: the
newsletter is now the feature, and everything else serves it.

- **Homepage leads with the newsletter.** The hero is "The Center's
  resources, delivered to your Cornell inbox", with a subscribe box
  right below it and what subscribers get (resources featured in every
  issue; conference funding and deadlines — Grace Hopper, Tapia, Code
  Afrique; events and programs). Nav puts Newsletter first, before
  Audiences / Newsletter Issues. The `/newsletter` page is the primary
  page, not a side page.
- **Issues are built from the real resources.** The campaign composer
  is reframed as composing a newsletter issue: staff pick resources
  from the platform's real 25 resources to feature (checkbox list with
  title + category + link), plus a subject and message. Preview renders
  the issue with the chosen resources and the exact recipient count.
  Sending goes to confirmed newsletter subscribers and/or selected
  audiences — an issue can go to subscribers alone, with no audience
  picked. Campaigns are newsletter issues under the hood: same model
  and statuses (`draft` / `queued` / `sent` / `partially_sent`),
  per-recipient status, no-SMTP → "ready to send", never falsely
  marked sent. The sent email appends a "Featured resources" section
  (title + link + description) to the staff message.
  Backend: `Campaign.resource_ids` (JSON list of resource ids, in
  display order); `GET /api/campaigns/{id}` returns
  `featured_resources` (resolved rows) alongside the recipient count.
  Unknown resource ids are rejected (404). `include_self_signup`
  defaults on in the composer.
- **Cornell-domain signup.** Public newsletter signup accepts ONLY
  `@cornell.edu` emails — validated in the backend
  (`backend/app/mail.py`: `is_cornell_email`, shared error
  "Use your Cornell email to subscribe") and on the frontend (homepage
  subscribe box and `/newsletter` page), with that message shown.
  Double opt-in stays.
- **Imported org contacts are unchanged** — staff vets those lists
  (CSV upload, manual add, org-rep submission). **Note for staff:**
  imported contacts should be Cornell students, since the newsletter
  goes to the Cornell domain.
- **Recipient math fix found by the new tests:** a subscribers-only
  issue used to also pull in every org contact, because the recipient
  query ran unfiltered when no audience was selected. Fixed in
  `_campaign_recipients`: contacts contribute only when the issue
  targets an audience or an org filter; a subscribers-only issue goes
  to subscribers alone.
- **Upgrade note:** `Campaign.resource_ids` is a new column. A fresh
  database gets it from `create_all`; an existing SQLite file from the
  Nov 10 build does not (SQLAlchemy never alters existing tables).
  The Render deploy uses ephemeral container storage, so a redeploy
  starts fresh — but if the database is ever moved to persistent
  Postgres, add the column once:
  `ALTER TABLE campaigns ADD COLUMN resource_ids TEXT NOT NULL DEFAULT '[]';`

The opt-in newsletter self-signup is now the core channel — the org
audiences feed it (they are who the issues go to), they are not a
separate second channel.

## Core rebuild (Nov 10, 2026) — the reach-first reframe

jem reviewed the Nov 6 rebuild and said the core functionality and goal
were missing: the platform has to **reach** the students who need the
Center, not just list resources. Rebuilt around that core; the homepage
now leads with audiences, campaigns, and booking. Resources and
conferences are still there, reachable but not the lead. Nothing was
pushed; no live service was touched.

**CORE 1 — Audience intake from orgs** (`backend/app/models.py`: Audience,
Contact, OrgSubmission; `backend/app/main.py`: `/api/audiences/*`,
`/api/org-submissions/*`; `frontend/app/audiences/page.tsx`,
`frontend/app/org-submit/page.tsx`):

- Staff create audiences tied to a source org (NSBE, URMC, CampusGroups,
  or a custom org name) and add contacts three ways: CSV upload
  (`name, email, org, interests`; downloadable template at
  `GET /api/audiences/contacts/template`, preview step showing how many
  rows will import and why the rest will not, then a confirm import),
  manual add (one contact at a time), or an org-rep submission form
  (public page `/org-submit`; paste lines or upload a CSV).
- Org-rep submissions land as **pending review** — staff approve them
  into an audience (or reject them); they are never auto-added. Approving
  without choosing an audience creates one named after the org.
- Contacts store name, email, source org, interests/tags, source
  (`upload` / `manual` / `org-submission` / `self-signup`), and opt-out
  status. Opted-out contacts are excluded from every campaign recipient
  count. **Zero contacts are seeded.**
- **Permission note (honest, in the UI and here):** orgs share their lists
  only with their agreement. The platform provides the intake — it does
  not take lists. No org contacts, rosters, or agreements were invented.
- **Cornell-domain note (Nov 20, 2026):** imported contacts should be
  Cornell students — the newsletter goes to students at the Cornell
  domain. Staff vets the lists; the platform does not enforce the
  domain on imports (only public self-signup is Cornell-only).

**CORE 2 — Newsletter issues (was "Email campaigns")**
(`backend/app/models.py`: Campaign, CampaignRecipient;
`backend/app/mail.py`; `backend/app/main.py`: `/api/campaigns/*`;
`frontend/app/campaigns/page.tsx`):

- Staff compose a newsletter issue (subject, message, sender name),
  pick resources from the platform's real resource list to feature in
  it, pick audiences and/or filter by org or interest, optionally
  include confirmed newsletter subscribers (on by default — an issue
  can go to subscribers alone), preview the exact recipient count
  (opted-out excluded) with the featured resources shown, and send.
- Sending transport is **SMTP via env vars** (see below). When SMTP is
  not configured, sending saves the campaign as **"ready to send"**
  (`status=queued`) with its full content and recipient list visible and
  a banner explaining that sending needs SMTP credentials. **A queued
  campaign is never shown as sent** — the status is `queued`, and the
  send response says so plainly.
- Statuses: `draft` / `queued` / `sent` / `partially_sent`; per-recipient
  status (`sent` / `failed` + error) is recorded when actually sent.
  Dashboard aggregates come from real DB rows only. The sent email
  appends the featured resources (title + link + description) to the
  staff message.

**SMTP env vars (set in the Render dashboard → service → Environment):**

| Var | Example |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` or `smtp.sendgrid.net` |
| `SMTP_PORT` | `587` (STARTTLS) or `465` (implicit TLS) |
| `SMTP_USER` | Gmail address, or `apikey` for SendGrid |
| `SMTP_PASS` | Gmail **app password** (not the account password), or a SendGrid API key |
| `SMTP_FROM` | The address campaigns send from, e.g. `deib-office@bowers.cornell.edu` |

If any of these is unset, the mailer is off and campaigns queue instead
of sending. For Gmail, create the app password at Google Account →
Security → 2-Step Verification → App passwords. For SendGrid, create an
API key with Mail Send permission and use `SMTP_USER=apikey`.

**CORE 3 — Real appointment booking with Dr. Roberts**
(`backend/app/models.py`: AvailabilitySlot, Booking;
`backend/app/main.py`: `/api/slots/*`, `/api/bookings/*`;
`frontend/app/appointments/page.tsx`, dashboard slots/bookings section):

- The old request-form-that-sits-in-a-list is gone (the `Appointment`
  model is kept only as a deprecated table; no endpoint uses it).
- Staff/admin create availability slots (date, start/end time, type:
  call or in-person, host defaults to Dr. LeeAnn Roberts). The public
  booking page lists **open** slots only; a visitor picks one, enters
  name + Cornell email + purpose, and the slot becomes **booked** with a
  confirmation shown. Staff view lists bookings and can cancel one,
  which re-opens the slot. Double-booking is rejected (409).
- **No slots or times are invented — slots start empty until an admin
  adds them.** Dr. Roberts (or staff) adds her availability through the
  dashboard. Contact `deib-office@bowers.cornell.edu` stays visible on
  the booking page.

> **Superseded Nov 20, 2026** — the newsletter is now the core feature
> (see "Newsletter as the core" above). The opt-in self-signup is the
> core channel; the org audiences feed it.

## What was built

**Backend** (`backend/`, FastAPI + SQLAlchemy, Python 3.12):

- `app/database.py` — Postgres when `DATABASE_URL` is set, otherwise a
  local SQLite file (`sqlite:///./bowers.db`). The old default pointed at
  a docker-compose host that does not exist outside compose; the default
  is now SQLite.
- `app/models.py` — User, SessionToken, Resource, Conference,
  ConferenceParticipation, Event, NewsletterSubscriber, Appointment
  (deprecated — see Core 3), OutreachEntry (old shape + `channel`,
  `audience`, `subject`), plus the core models: Audience, Contact,
  OrgSubmission, Campaign, CampaignRecipient, AvailabilitySlot, Booking.
- `app/mail.py` — stdlib-only SMTP sender (`smtplib`): port 465 =
  implicit TLS, otherwise STARTTLS; `smtp_configured()` gate; an
  unsubscribe footer is appended to every campaign.
- `app/auth.py` — stdlib-only auth: `hashlib.pbkdf2_hmac` passwords with a
  per-user salt, `secrets.token_urlsafe` session tokens in the DB with
  7-day expiry, Bearer auth. Roles: student, faculty, admin.
- `app/main.py` — all endpoints in the frontend contract (health, auth
  incl. role promotion, resources, conferences + participation, events,
  newsletter double opt-in, audiences + contacts + CSV upload, org
  submissions + review, campaigns + send, slots + bookings, outreach,
  dashboard, reports summary). Admin-only writes return 403 for
  non-admins, 401 when unauthenticated. Serves a built frontend from
  `../frontend/out` with an SPA fallback for non-`/api` paths when it
  exists. CORS allows localhost:3000 and `$FRONTEND_URL`.
- `app/seed.py` — replaced entirely with the real content from
  REAL-SPEC.md §7.1 only: 25 resources (4 office services, 20 community
  resources, 1 campus-partners row), 5 conferences, 10 events, and one
  demo admin. **No** participation rows, subscribers, appointments, or
  outreach entries are seeded — those are tracked going forward only.
  Grace Hopper Celebration 2026 is seeded `status=cancelled` (never
  upcoming); Tapia 2027 is `tba` with a null date; no event dates were
  invented (all null).
- `backend/verify_backend.py` — stdlib-only end-to-end test suite (see
  Verification below). Run it with `python3 verify_backend.py` from
  `backend/` using the venv. Now **111 checks** (60 from Nov 6 + 40 for
  the core, Nov 10, + 11 for the newsletter reframe, Nov 20).
- `backend/requirements.txt` — added `python-multipart>=0.0.9` (required
  for `Form` / `UploadFile` — CSV uploads and the org-submission file
  path fail to import without it).
- `backend/Dockerfile` — multi-stage: `node:20` builds the frontend
  (`npm ci` + `npm run build`, static export to `frontend/out`),
  `python:3.12-slim` installs the backend and serves both API and
  frontend from one process on `$PORT`.
- `frontend/next.config.js` — added `output: "export"` so the frontend
  builds to a static `out/` directory the backend can serve. All pages
  are client components that fetch the API at runtime, so this is safe.

**Deploy** (`render.yaml`, project root): one free Docker web service
(`bowers-di-platform`, `dockerfilePath: backend/Dockerfile`,
`dockerContext: .`, `healthCheckPath: /api/health`). `DATABASE_URL` is
`sync: false` (unset by default → SQLite fallback).

**Demo admin (demo only — change before any real use):**
`admin@center.demo` / `demo1234`. Registration always creates role
`student`; requesting admin/faculty at signup is rejected (400). An admin
promotes roles via `PATCH /api/auth/users/{id}/role`.

## Database note

Render allows only one free Postgres per workspace and it is already used
by another project, so no managed Postgres is provisioned here. The
default deploy runs on SQLite (`bowers.db` inside the container). That
is fine for a demo, but container storage is ephemeral: **for persistent
multi-user data, set `DATABASE_URL` to a Neon Postgres URL** (free tier)
in the Render dashboard. The same code runs on both.

`docker-compose.yml` was left as-is for local dev (its `api` service
already sets `DATABASE_URL` to the compose `db` Postgres service).

## Newsletter / SMTP note

There is **no mail server wired up here** — see "CORE 2" above for the
SMTP env vars. Until they are set, issues queue as "ready to send"
and nothing is sent.

Newsletter signup is double opt-in **and Cornell-only**: public signup
accepts `@cornell.edu` addresses only, validated in the backend
(`POST /api/newsletter/signup` → 400 "Use your Cornell email to
subscribe" otherwise) and on the frontend (homepage subscribe box and
`/newsletter` page). `POST /api/newsletter/signup` returns a
`confirmation_token` and `confirmation_url`, which the frontend shows on
the signup confirmation page; `GET /api/newsletter/confirm?token=…`
confirms. Once SMTP is configured, the confirmation link can be emailed
instead — the signup endpoint is the one place to add that send.

**Audience rule (updated Nov 10, 2026; newsletter reframe Nov 20,
2026):** the platform now takes in org lists through the intake (CSV
upload, manual add, org-rep submission) — but only with the org's
agreement, and submissions are pending review until staff approve them.
The platform provides the intake; it never takes a list. Imported
contacts should be Cornell students, since the newsletter goes to the
Cornell domain — staff vets the lists. Anyone can opt out, and
opted-out contacts are excluded from every issue.

## How to run it locally

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/api/health  {"status":"ok"}
# → demo admin: admin@center.demo / demo1234
```

With Postgres instead:

```bash
DATABASE_URL=postgresql://user:pass@host:5432/db \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

With the frontend served too:

```bash
cd frontend && npm install && npm run build   # produces frontend/out
cd ../backend && .venv/bin/python -m uvicorn app.main:app --port 8000
# → http://127.0.0.1:8000/ serves the built site; /api/* still the API
```

Run the tests: `cd backend && .venv/bin/python verify_backend.py`
(boots its own server on a throwaway SQLite DB on port 8123).

## Verification (this VM, Nov 6 + Nov 10 + Nov 20, 2026)

- Deps install clean in a fresh venv: fastapi 0.162.0, sqlalchemy 2.1.8,
  uvicorn + psycopg2-binary (no new dependencies added).
- `verify_backend.py`: **111/111 checks passed** (60 from Nov 6 +
  40 for the core, Nov 10, + 11 for the newsletter reframe, Nov 20),
  including: auth register/login/me, role enforcement (403s for students,
  401s when unauthenticated, admin promotion), resource list/search,
  conference seed correctness (GHC 2026 `cancelled`, never in
  `?upcoming=true`; Tapia 2026 past; Code Afrique 2026 past; GHC India
  upcoming; Tapia 2027 `tba`/null date), newsletter signup → confirm →
  re-signup (`already_subscribed`) → pending re-issue → unsubscribe,
  participation (own attendance + admin listing + 403 for recording for
  someone else), dashboard and reports summary computed from real rows
  only.
- **Newsletter reframe checks (Nov 20, in the same suite):**
  non-Cornell signup → 400 "Use your Cornell email to subscribe";
  `@cornell.edu` signup → 201 + token → confirm works; issue compose
  with 2 real resources → 201 with `featured_resources` listing both
  titles and the correct recipient count; issue detail preview shows
  the featured resources; unknown resource id → 404; issue send with
  no SMTP → `queued`, never `sent`; subscribers-only issue → 201 with
  only the 2 confirmed subscribers (recipient-math fix: contacts no
  longer leak into a subscribers-only issue); edit draft issue
  resources; dashboard/reports totals on the new rows (4 subscribers /
  2 confirmed, 4 campaigns: 2 draft, 2 queued).
- Integrated live run (Nov 20, fresh SQLite DB, seeded, server on port
  8125, built frontend served): **27/27 checks passed** proving the
  newsletter core end to end — non-Cornell signup rejected, Cornell
  signup → confirm → subscribed; staff composes an issue picking 2 real
  resources → preview shows them + correct recipient count (2 contacts
  + 1 subscriber, opted-out excluded); send with no SMTP queues as
  "ready to send" with content + recipients visible, never marked sent;
  admin adds a slot → visitor books it → slot shows booked + booking
  appears in staff view → cancel re-opens it; unauthenticated dashboard
  → 401; homepage serves 200 with the newsletter-first copy and the
  built bundles carry the newsletter-first strings.
- Frontend static export verified (Nov 20): `npm run build` succeeds
  with `output: "export"` — **15 static pages** (home + 12 content
  pages + login/register + 404), no errors; all content pages serve
  200 from the static export (deep routes via the SPA fallback; their
  strings are in the built JS bundles).
- **Core checks (Nov 10, in the same suite):** audience create + list;
  CSV template download; CSV upload preview (3 valid / 1 invalid, errors
  listed, sample shown) then confirm import (3 imported / 1 skipped);
  duplicate email in an audience → 409; manual add; opt-out flag;
  org-submission (JSON + multipart CSV) → pending → staff approve adds
  contacts to a new org-named audience / reject; campaign create with
  recipient math (opted-out excluded, interest/org filters, self-signup
  inclusion toggle); campaign send with **no SMTP → `queued`, never
  `sent`**; slot create → open list → book (non-Cornell email → 400,
  double-book → 409) → booked → staff list → cancel re-opens;
  dashboard/reports totals on the new rows (audiences, contacts,
  opted-out, campaigns, slots, bookings).
- Integrated live run (Nov 10, fresh SQLite DB, seeded, server on
  port 8123): **30/30 checks passed** proving the core end to end —
  CSV upload creates an audience with contacts; org-submission →
  staff approval adds them; campaign preview shows the correct
  recipient count → send with no SMTP queues as "ready to send" with
  content + recipients visible, never marked sent; admin adds a slot →
  visitor books it → slot shows booked + booking appears in staff view
  → cancel re-opens it; opt-in signup still works; unauthenticated
  dashboard → 401; dashboard totals from real rows.
- Frontend static export verified (Nov 10): `npm run build` succeeds
  with `output: "export"` — **15 static pages** (home + 12 content
  pages + login/register + 404), no errors; all 12 content pages serve
  200 from the static export. Staff pages (audiences, campaigns,
  dashboard) prerender as "Loading…" and render client-side after the
  auth check — same as the Nov 6 dashboard; their UI strings are in the
  built JS bundles.
- Default SQLite fallback verified: with no `DATABASE_URL`, the server
  creates `./bowers.db`, seeds the demo admin + 25 resources + 5
  conferences + 10 events, and serves them.
- Standalone seed verified: `python -m app.seed` → 1 user, 25 resources,
  5 conferences, 10 events, 0 participation / subscribers / appointments
  / outreach rows.
- Frontend static export verified: `npm run build` succeeds with
  `output: "export"` (12 routes) and the backend serves `frontend/out`
  (`/` → 200 index, `/resources` and `/dashboard` → 200 via SPA
  fallback, `/api/health` → JSON, unknown `/api/*` → 404).
- Two real bugs found and fixed during verification: Pydantic field/type
  name shadowing on `date` (`ConferenceBase`, `OutreachBase`) — fixed by
  aliasing the imported type to `_date`.

**Not verified here (needs a browser / live service):**

- The full Docker image build (`docker` is not installed in this VM) —
  the Dockerfile stages mirror the two builds that were verified
  separately (frontend `npm run build`, backend venv install + server),
  but the combined image was never built or run. Note the Dockerfile
  now installs `python-multipart` via `requirements.txt` — no Dockerfile
  change was needed for the CSV upload support.
- The Render deploy itself (nothing pushed, no service created).
- **Real SMTP sending** — the mailer was verified only as far as the
  no-SMTP gate (campaigns queue, never claim sent). An actual send
  through Gmail/SendGrid has not been tested; after the first deploy,
  set the SMTP env vars and send a test campaign to a small audience
  before using it for real outreach.
- The rebuilt frontend pages against this API in a real browser — the
  API contract is the one the frontend uses, and the static export
  serves, but no browser click-through was done (audiences CSV upload,
  campaign compose/send, slot booking, org-submit form).

## Open questions (only jem / the Center can answer)

1. **Login method:** who logs in and how — Cornell NetID/SSO, email
   allowlist, or open registration? Who approves accounts? (Current
   build: open registration as `student`, admin promotes.)
2. **Faculty workflow:** faculty is a named role but has no described
   use in the platform. What do faculty do here, if anything?
3. **GHC handling:** GHC 2026 is listed as cancelled; GHC India Jan
   20–22, 2027 is listed as upcoming. Is that the right split, or
   should GHC be kept only as a past program until the next US cycle is
   announced?
4. **Appointment mechanics:** slot-based booking is built — staff/admin
   add Dr. Roberts' availability and visitors book open slots. What
   times does she actually offer, and who adds them (her, or staff on
   her behalf)? Slots start empty until someone adds them.
5. **Newsletter / campaign mechanics:** SMTP env vars are documented
   above (Gmail app password or SendGrid). Who sends from which account
   — `deib-office@bowers.cornell.edu` is the suggested sender — and
   whether CampusGroups integration is actually available. Org rosters
   are now handled by the intake with the org's agreement (see Core 1).
