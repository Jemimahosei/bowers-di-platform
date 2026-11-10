# Bowers D&I Platform — Deploy Notes

Backend rebuilt Nov 6, 2026 to the real spec (`REAL-SPEC.md`). Nothing was
pushed; no live service was touched.

## What was built

**Backend** (`backend/`, FastAPI + SQLAlchemy, Python 3.12):

- `app/database.py` — Postgres when `DATABASE_URL` is set, otherwise a
  local SQLite file (`sqlite:///./bowers.db`). The old default pointed at
  a docker-compose host that does not exist outside compose; the default
  is now SQLite.
- `app/models.py` — User, SessionToken, Resource, Conference,
  ConferenceParticipation, Event, NewsletterSubscriber, Appointment,
  OutreachEntry (old shape + `channel`, `audience`, `subject`).
- `app/auth.py` — stdlib-only auth: `hashlib.pbkdf2_hmac` passwords with a
  per-user salt, `secrets.token_urlsafe` session tokens in the DB with
  7-day expiry, Bearer auth. Roles: student, faculty, admin.
- `app/main.py` — all endpoints in the frontend contract (health, auth
  incl. role promotion, resources, conferences + participation, events,
  newsletter double opt-in, appointments, outreach, dashboard, reports
  summary). Admin-only writes return 403 for non-admins, 401 when
  unauthenticated. Serves a built frontend from `../frontend/out` with an
  SPA fallback for non-`/api` paths when it exists. CORS allows
  localhost:3000 and `$FRONTEND_URL`.
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
  `backend/` using the venv.
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

There is **no mail server wired up here**. Newsletter signup is double
opt-in: `POST /api/newsletter/signup` returns a `confirmation_token` and
`confirmation_url`, which the frontend shows on the signup confirmation
page; `GET /api/newsletter/confirm?token=…` confirms. Wiring SendGrid or
another SMTP service would let the confirmation link be emailed instead —
the signup endpoint is the one place to add that send.

**Opt-in-only audience rule:** the subscriber list is built from people
who sign up themselves. The platform must NOT import student-org member
lists (URMC, NSBE) or CampusGroups rosters without those orgs' explicit
permission — that access is still unsettled (see open questions).

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

## Verification (this VM, Nov 6, 2026)

- Deps install clean in a fresh venv: fastapi 0.162.0, sqlalchemy 2.1.8,
  uvicorn + psycopg2-binary (no new dependencies added).
- `verify_backend.py`: **60/60 checks passed**, including: auth
  register/login/me, role enforcement (403s for students, 401s when
  unauthenticated, admin promotion), resource list/search, conference
  seed correctness (GHC 2026 `cancelled`, never in `?upcoming=true`;
  Tapia 2026 past; Code Afrique 2026 past; GHC India upcoming; Tapia
  2027 `tba`/null date), newsletter signup → confirm → re-signup
  (`already_subscribed`) → pending re-issue → unsubscribe, appointment
  submit → staff list → confirm, participation (own attendance + admin
  listing + 403 for recording for someone else), dashboard and reports
  summary computed from real rows only.
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
  but the combined image was never built or run.
- The Render deploy itself (nothing pushed, no service created).
- The rebuilt frontend pages against this API in a real browser — the
  API contract is the one the frontend builder is using, and the static
  export serves, but no browser click-through was done.

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
4. **Appointment mechanics:** what times does Dr. Roberts offer, and
   through what — a form that emails the office (current build: staff
   confirm in the admin view), a calendar link, or something else?
5. **Newsletter mechanics:** opt-in signup (current build) vs org
   rosters; who sends from which account; whether CampusGroups
   integration is actually available.
