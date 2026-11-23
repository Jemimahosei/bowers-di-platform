# Open Door — Deploy Notes

Backend rebuilt Nov 6, 2026 to the real spec (`REAL-SPEC.md`). Nothing was
pushed; no live service was touched.

## Email sending via Resend (Nov 21, 2026) — the newsletter actually sends

SMTP cannot work on Render's free tier: Render blocks outbound SMTP
ports (25/465/587), so a Gmail app password or SendGrid SMTP can never
send from the live deploy (proven on braidedU the same day — its Gmail
SMTP failed "Network is unreachable" on Render). The sender is now
Resend, over plain HTTPS — the same setup already delivering for
braidedU.

- **Senders, in priority order** (`backend/app/mail.py`): SMTP when
  fully configured (`SMTP_HOST` + `SMTP_USER` + `SMTP_PASS` — still
  first, for local dev or any host that allows SMTP), else Resend when
  `RESEND_API_KEY` is set, else nothing sends (campaigns queue as
  "ready to send", signups fall back to the /newsletter-only link).
  `email_configured()` / `email_mode()` (`'smtp'` | `'resend'` |
  `'console'`) / `last_error()` report the state; `GET /api/health`
  returns `email_mode` and `last_email_error` (never any secret).
- **Env vars to set in the Render dashboard** (service → Environment):
  `RESEND_API_KEY` = the Resend API key (from the Resend dashboard —
  the same key braidedU uses), `RESEND_FROM` = the sender, default
  `Center for Belonging <hello@jemimahosei.com>` (jemimahosei.com is
  the domain verified in Resend). No new dependency: the Resend send
  is stdlib `urllib` only, with a custom User-Agent — Resend sits
  behind Cloudflare, which refuses Python's default User-Agent with
  error 1010.
- **The Gmail route is dead for the live deploy.** The app-password
  plan from Nov 20 is superseded: no `SMTP_*` vars are needed on
  Render, and the Gmail app password jem created is unused there.
  The confirmation email body is unchanged (plain ASCII, `cte="7bit"`,
  long URL never folded) and the senders raise on failure, so the
  callers' contracts are unchanged — signup falls back to the
  /newsletter-only link, campaign send records per-recipient failure.
- **After this is pushed:** set the two vars in the Render dashboard,
  redeploy, then send a test issue to a small audience (and sign up
  with a Cornell address) and check the inbox before using it for
  real outreach. A real Resend send has not been tested yet (see
  "Not verified here" below).

## Email confirmation (Nov 20, 2026) — the confirmation email is the channel

jem: when someone signs up with their name, they should receive an
email asking them to confirm their subscription. So the confirmation
email is now the channel — not an on-page link.

- **What happens on signup.** `POST /api/newsletter/signup` still
  creates the pending subscriber and token, then — when email is
  configured — sends the confirmation email (`backend/app/mail.py`:
  `send_confirmation_email`). The email is addressed by name
  ("Hi [Name]," — "Hi there," when no name was given, e.g. the
  homepage form is email-only), says they signed up for the Center
  for Belonging newsletter, carries the confirmation link, and says
  what they'll get (resources and opportunities in every issue).
  From address = `RESEND_FROM` (Resend) or `SMTP_FROM` (SMTP, when
  that is the active sender). The confirm endpoint and token flow are
  unchanged; double opt-in stays (an unconfirmed address receives
  nothing else).
- **What the page shows.** After signup, the page shows "Check your
  inbox — we sent a confirmation email to [their Cornell address]"
  (plus a note to check spam). **No confirmation link or button on
  the homepage, ever.**
- **Fallback only when no email sender is configured.** If sending fails because no
  mail server is configured, the API answers `email_sent: false` +
  the token, and the frontend shows the confirmation link on
  **/newsletter only**, clearly labeled as a temporary fallback ("No
  mail server is connected yet, so your confirmation link is shown
  here — once the Center connects its email account, this will arrive
  by email instead"). When email is configured, no on-page link
  appears anywhere. If email is configured but the send itself fails,
  the same /newsletter-only link appears with a "we couldn't send
  it" label. Nothing is ever claimed sent when it was not.
- **The URL must not fold (bug found by the test).** The first
  version of the email came out quoted-printable, which folds long
  lines at 76 chars — and the confirmation URL is long enough to be
  split mid-token, which breaks the link for anyone who copies it.
  The confirmation email is therefore plain ASCII with
  `cte="7bit"`, so the URL line goes out whole. (Campaign emails
  still use the default encoding — staff-composed content, unchanged.)
- **Sender (decided by jem, Nov 20, 2026; route changed Nov 21, 2026).**
  The Bowers emails send from her verified domain via Resend (see
  "Email sending via Resend" above):
  `RESEND_API_KEY` = the Resend API key,
  `RESEND_FROM` = `Center for Belonging <hello@jemimahosei.com>`.
  The env vars are set in the Render dashboard → service →
  Environment after this rework is pushed. Until they are set,
  signups use the /newsletter-only fallback link and issues queue as
  "ready to send". The Gmail SMTP plan from Nov 20 (`SMTP_HOST` =
  `smtp.gmail.com`, `SMTP_USER`/`SMTP_FROM` =
  `writesaifreewalter@gmail.com`, Gmail app password) is superseded —
  Render's free tier blocks outbound SMTP ports, so it cannot send
  from the live deploy; SMTP stays first-priority only where a host
  allows it (e.g. local dev).

## Welcoming homepage + routing fixes (Nov 20, 2026)

jem looked at the live homepage and said the main page should welcome
students and prompt them to sign up for a constant supply of resources
and opportunities. She had just signed up with her Cornell email and
the homepage was showing the post-signup confirmation box. Reworked:

- **Welcoming hero, speaking to students.** The hero now welcomes
  students directly ("Welcome — the Center's resources and
  opportunities, in your inbox") and invites them to sign up once for
  a steady, ongoing supply: every issue brings real resources plus
  opportunities (conference funding and deadlines, scholarships and
  paid opportunities, events and programs). The "You belong here." —
  Hakim Weatherspoon quote stays, as does the Cornell design. The
  signup prompt is in the hero itself: Cornell email field + Sign up
  button, one line saying Cornell email only.
- **Confirmation step moved off the homepage.** After signing up on
  the homepage, the page shows only a short note ("You're almost in —
  head to the newsletter page to confirm your subscription"). The full
  confirmation step (confirmation link + Confirm button + the honest
  no-email note) lives on /newsletter only. Same endpoint and token
  flow — only the placement changed. The homepage hands the token to
  /newsletter via sessionStorage (`opendoor-pending-confirmation`); if
  that handoff is lost (e.g. a new tab), signing up again on
  /newsletter issues a fresh token, so the step still works.
- **What you'll get, every issue.** A section below the hero frames
  the subscription as an ongoing supply: real resources in every
  issue, opportunities, events and programs. Real content only.
- **Sub-routes serve their own pages (live-verification finding).**
  The backend's static fallback served the root homepage for every
  extensionless sub-route (`/appointments`, `/campaigns`, …),
  because it only served a path when it was a file — and the Next.js
  static export (trailingSlash) puts each route in its own directory
  with an `index.html`. Fixed in `backend/app/main.py`: a directory
  path now serves its own `index.html`. Direct loads and in-app
  navigation to /appointments (the real slot-booking page) now render
  that page.
- **HTML is no longer cached.** Plain loads of `/` were serving the
  previous design minutes after a deploy went Live, with no GET /
  entries in the deploy logs — a cached copy in front of the new
  instance. Fixed in `backend/app/main.py`: HTML responses now carry
  `Cache-Control: no-cache` (revalidate every load), so a redeploy
  shows the new pages immediately. Hashed JS/CSS under `/_next/static`
  keep their default caching.

## Newsletter as the core (Nov 20, 2026) — the reach reframe

jem: the newsletter should be the core feature, because it sends the
resources to students at the Cornell domain. Reframed around that: the
newsletter is now the feature, and everything else serves it.

- **Homepage leads with the newsletter.** The hero welcomes students
  ("Welcome — the Center's resources and opportunities, in your
  inbox"), with a signup prompt right in the hero and what subscribers
  get below it (resources featured in every issue; conference funding
  and deadlines — Grace Hopper, Tapia, Code Afrique; events and
  programs). Nav puts Newsletter first, before Audiences / Newsletter
  Issues. The `/newsletter` page is the primary page, not a side page.
- **Issues are built from the real resources.** The campaign composer
  is reframed as composing a newsletter issue: staff pick resources
  from the platform's real 25 resources to feature (checkbox list with
  title + category + link), plus a subject and message. Preview renders
  the issue with the chosen resources and the exact recipient count.
  Sending goes to confirmed newsletter subscribers and/or selected
  audiences — an issue can go to subscribers alone, with no audience
  picked. Campaigns are newsletter issues under the hood: same model
  and statuses (`draft` / `queued` / `sent` / `partially_sent`),
  per-recipient status, no email sender → "ready to send", never falsely
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
- Sending transport is **Resend via env vars** (see below; SMTP first
  when fully configured, for hosts that allow it). When no email
  sender is configured, sending saves the campaign as **"ready to send"**
  (`status=queued`) with its full content and recipient list visible and
  a banner explaining that sending needs an email sender configured.
  **A queued campaign is never shown as sent** — the status is `queued`, and the
  send response says so plainly.
- Statuses: `draft` / `queued` / `sent` / `partially_sent`; per-recipient
  status (`sent` / `failed` + error) is recorded when actually sent.
  Dashboard aggregates come from real DB rows only. The sent email
  appends the featured resources (title + link + description) to the
  staff message.

**Resend env vars (set in the Render dashboard → service → Environment):**

| Var | Example |
| --- | --- |
| `RESEND_API_KEY` | The Resend API key (from the Resend dashboard — same key braidedU uses) |
| `RESEND_FROM` | `Center for Belonging <hello@jemimahosei.com>` (jemimahosei.com is the domain verified in Resend; a bare address is wrapped with the sender name) |

SMTP is still supported as the first-priority sender where a host
allows it — `SMTP_HOST`, `SMTP_PORT` (`587` STARTTLS or `465`
implicit TLS), `SMTP_USER`, `SMTP_PASS` (a Gmail **app password**,
not the account password, or a SendGrid API key with `SMTP_USER` =
`apikey`), `SMTP_FROM` — but **it cannot work on Render's free tier**
(Render blocks outbound SMTP ports 25/465/587), so on the live deploy
Resend is the sender that works. If no sender is configured at all,
the mailer is off and campaigns queue instead of sending.

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
  local SQLite file (`sqlite:///./opendoor.db`). The old default pointed at
  a docker-compose host that does not exist outside compose; the default
  is now SQLite.
- `app/models.py` — User, SessionToken, Resource, Conference,
  ConferenceParticipation, Event, NewsletterSubscriber, Appointment
  (deprecated — see Core 3), OutreachEntry (old shape + `channel`,
  `audience`, `subject`), plus the core models: Audience, Contact,
  OrgSubmission, Campaign, CampaignRecipient, AvailabilitySlot, Booking.
- `app/mail.py` — stdlib-only sender: SMTP via `smtplib` (port 465 =
  implicit TLS, otherwise STARTTLS) first when fully configured, else
  Resend via stdlib `urllib` (HTTPS POST to api.resend.com, custom
  User-Agent); `email_configured()` / `email_mode()` / `last_error()`
  gates and reporting; an unsubscribe footer is appended to every
  campaign. `GET /api/health` reports `email_mode` and
  `last_email_error`.
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
  `backend/` using the venv. Now **112 checks** (60 from Nov 6 + 40 for
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
(`opendoor`, `dockerfilePath: backend/Dockerfile`,
`dockerContext: .`, `healthCheckPath: /api/health`). `DATABASE_URL` is
`sync: false` (unset by default → SQLite fallback).

**Demo admin (demo only — change before any real use):**
`admin@center.demo` / `demo1234`. Registration always creates role
`student`; requesting admin/faculty at signup is rejected (400). An admin
promotes roles via `PATCH /api/auth/users/{id}/role`.

## Database note

Render allows only one free Postgres per workspace and it is already used
by another project, so no managed Postgres is provisioned here. The
default deploy runs on SQLite (`opendoor.db` inside the container). That
is fine for a demo, but container storage is ephemeral: **for persistent
multi-user data, set `DATABASE_URL` to a Neon Postgres URL** (free tier)
in the Render dashboard. The same code runs on both.

`docker-compose.yml` was left as-is for local dev (its `api` service
already sets `DATABASE_URL` to the compose `db` Postgres service).

## Newsletter / email note

There is **no email sender configured on the live deploy yet** — see
"Email sending via Resend" above for the vars to set. Until they are
set, issues queue as "ready to send" and nothing is sent, and signups
use the /newsletter-only fallback link.

Newsletter signup is double opt-in **and Cornell-only**: public signup
accepts `@cornell.edu` addresses only, validated in the backend
(`POST /api/newsletter/signup` → 400 "Use your Cornell email to
subscribe" otherwise) and on the frontend (homepage subscribe box and
`/newsletter` page). The confirmation email is the channel (see
"Email confirmation" above): when email is configured the signup
response carries `email_sent: true` and no token, and the page shows a
"Check your inbox" note; when it is not configured the response
carries `email_sent: false` + the token, and the link appears on
/newsletter only, labeled as a temporary fallback.
`GET /api/newsletter/confirm?token=…` confirms.

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
# → http://127.0.0.1:8000/api/health  {"status": "ok", "email_mode": "console", "last_email_error": ""}
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
- `verify_backend.py`: **112/112 checks passed** (60 from Nov 6 +
  40 for the core, Nov 10, + 11 for the newsletter reframe, Nov 20,
  + 1 for the email-confirmation fallback, Nov 20),
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
- **Homepage rework + routing fixes + email confirmation (Nov 20,
  integrated run, fresh SQLite DB, server on port 8124, built
  frontend served): 41/41 checks passed with no SMTP configured
  (live-site state) and 48/48 with SMTP pointed at a local capturing
  server.** Direct GETs of `/`, `/campaigns`, `/appointments`,
  `/newsletter`, `/audiences`, `/org-submit` (plus trailing-slash
  variants) each return their own route's HTML, not the homepage;
  HTML carries `Cache-Control: no-cache`, hashed `/_next/static`
  assets keep default caching; homepage HTML carries the welcoming
  hero + signup prompt and no confirmation link/box (those strings
  live in the newsletter page's JS chunk only; the homepage chunk
  carries the "You're almost in" note + the sessionStorage handoff).
  SMTP mode: signup with name + `@cornell.edu` sends exactly one
  confirmation email ("Hi [Name],", the newsletter, what they'll get,
  the confirm link with a valid token, from `SMTP_FROM`); the
  response carries `email_sent: true` and no token; clicking the
  emailed link confirms the subscription; the campaign send actually
  sends. No-SMTP mode: signup returns `email_sent: false` + the
  fallback token, and the campaign send queues as "ready to send",
  never sent. Both modes: non-Cornell rejected, issue preview with 2
  featured resources + recipient count, slot booking end to end,
  unauthenticated dashboard → 401. **Real bug found by the SMTP run:**
  the first confirmation email came out quoted-printable, which folds
  long lines at 76 chars and split the confirmation URL mid-token —
  the email is now plain ASCII with `cte="7bit"` so the URL goes out
  whole (see "Email confirmation" above).
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
  creates `./opendoor.db`, seeds the demo admin + 25 resources + 5
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
- **Real sending through Resend** — the mailer was verified only as
  far as the no-sender gate (campaigns queue, never claim sent) and
  with the HTTP call mocked (see `backend/test_mail_resend.py`). An
  actual send through Resend has not been tested; after the first
  deploy, set `RESEND_API_KEY` / `RESEND_FROM` and send a test
  campaign to a small audience (and sign up with a Cornell address)
  before using it for real outreach. SMTP sending is likewise
  untested against a real server.
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
5. **Newsletter / campaign mechanics:** Resend env vars are documented
   above. Who sends from which account — `hello@jemimahosei.com` is
   the sender (the verified domain); `deib-office@bowers.cornell.edu`
   was the suggested sender under the old SMTP plan — and whether
   CampusGroups integration is actually available. Org rosters are
   now handled by the intake with the org's agreement (see Core 1).
