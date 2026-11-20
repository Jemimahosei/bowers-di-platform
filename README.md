# Bowers D&I Platform

The Center for Belonging's working tool at Cornell CIS Bowers (Cornell
Bowers College of Computing and Information Science). Its core job is
**reach**: get underrepresented students to the Center's resources and
actually use them. Tagline: *"You belong here."* — Hakim Weatherspoon,
Associate Dean for Belonging.

- **Student resource discovery** — the Center's real resources
  (consultations, advising, funding/proposal support, community resources,
  campus partners), searchable and filterable by category and audience,
  linking out to the real pages.
- **Conference participation tracking** — Tapia, Code Afrique, Grace
  Hopper (including GHC 2026, cancelled — listed as cancelled, never as
  upcoming), GHC India 2027. Participation is recorded per person going
  forward; no roster exists and none is invented.
- **Programs & events** — CSMore, Belonging at Bowers Awards, Dinner with
  the Deans+, EngageLEAP, Meta Days, Cornell alumni dinner, the weeklong
  immersive research workshop, the two-year career program, alumni
  mentorship groups, Impact Week.
- **Newsletter** — opt-in self-signup only (name, Cornell email,
  interests, topic preferences), double opt-in with a confirmation link.
  No member lists are taken from student orgs.
- **Appointment booking** — request an appointment or call with
  Dr. LeeAnn Roberts, Director of the DEIB office; requests go to the
  office for confirmation. Contact: deib-office@bowers.cornell.edu.
- **Staff dashboard & reporting** — participation trends, outreach log,
  subscriber growth, appointment queue, and a leadership report, all
  computed from real data.

Stack: **Next.js 15 + TypeScript** frontend (static export), **FastAPI +
SQLAlchemy** backend, **PostgreSQL** when `DATABASE_URL` is set, **SQLite**
fallback otherwise. Multi-role auth (students, faculty, admins).

Full product spec: `REAL-SPEC.md` (sourced from jem's chat, with line
numbers). Architecture: `ARCHITECTURE.md`. Deploy notes:
`DEPLOY_NOTES.md`.

## Run it locally

Backend (API + serves the built frontend):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/api/health  {"status":"ok"}
# → demo admin: admin@center.demo / demo1234 (demo only — change before real use)
```

With the frontend served too:

```bash
cd frontend && npm install && npm run build   # produces frontend/out
cd ../backend && .venv/bin/python -m uvicorn app.main:app --port 8000
# → http://127.0.0.1:8000/ serves the built site; /api/* is the API
```

Frontend dev server (API on :8000):

```bash
cd frontend && npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# → http://localhost:3000
```

Tests: `cd backend && .venv/bin/python verify_backend.py` (60 checks,
boots its own server on a throwaway SQLite DB).

Or with Docker Compose (Postgres + API + web, local dev only):

```bash
docker compose up --build
```

## Deploy

`render.yaml` at the project root: one free Docker web service
(`bowers-di-platform`, `dockerfilePath: backend/Dockerfile`,
`dockerContext: .`, health check `/api/health`). `DATABASE_URL` is
`sync: false` — unset by default, so the deploy runs on SQLite; set it to
a Neon Postgres URL for persistent multi-user data (Render's one free
Postgres is already used by another project). See `DEPLOY_NOTES.md`.

## API reference

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/health` | Liveness check |
| POST | `/api/auth/register` | Register (always role `student`) |
| POST | `/api/auth/login` | Login → Bearer token |
| GET | `/api/auth/me` | Current user |
| GET | `/api/auth/users` | List users (admin) |
| PATCH | `/api/auth/users/{id}/role` | Promote role (admin) |
| GET | `/api/resources?search=&category=&audience=` | List/search/filter resources |
| POST | `/api/resources` | Add a resource (admin) |
| GET | `/api/resources/{id}` | One resource |
| GET | `/api/conferences` | Conferences (`?upcoming=true` filters) |
| POST | `/api/conferences` | Add a conference (admin) |
| GET/POST | `/api/conferences/{id}/participation` | Participation records |
| GET | `/api/events` | Programs & events |
| POST | `/api/events` | Add an event (admin) |
| POST | `/api/newsletter/signup` | Opt-in signup → confirmation token/URL |
| GET | `/api/newsletter/confirm?token=` | Confirm subscription |
| POST | `/api/newsletter/unsubscribe` | Unsubscribe |
| GET | `/api/newsletter/subscribers` | Subscribers (admin) |
| POST | `/api/appointments` | Request an appointment (public) |
| GET | `/api/appointments` | Appointment queue (admin) |
| PATCH | `/api/appointments/{id}` | Confirm/decline/complete (admin) |
| GET | `/api/outreach` | Outreach log (admin) |
| POST | `/api/outreach` | Add an outreach entry (admin) |
| GET | `/api/dashboard` | Staff dashboard aggregates (admin) |
| GET | `/api/reports/summary` | Leadership report (admin) |

## Project structure

```
render.yaml                 # one free Docker web service on Render
ARCHITECTURE.md             # components, data model, scaling
DEPLOY_NOTES.md             # deploy steps, verification, open questions
REAL-SPEC.md                # the real spec, sourced from jem's chat
docker-compose.yml          # postgres + api + web (local dev)
backend/
  app/
    main.py                 # FastAPI app + all endpoints + static serving
    models.py               # User, Resource, Conference, Event, ...
    schemas.py              # Pydantic request/response shapes
    auth.py                 # PBKDF2 passwords, session tokens, roles
    seed.py                 # REAL seed data only (25 resources, 5 confs, 10 events)
    database.py             # Engine/session, DATABASE_URL config
  requirements.txt
  Dockerfile                # multi-stage: node builds frontend, python serves
  verify_backend.py         # 60-check end-to-end suite
frontend/
  app/
    page.tsx                # Home + "You belong here" + impact stats
    resources/page.tsx      # Searchable, filterable resource discovery
    conferences/page.tsx    # Upcoming / past / cancelled conferences
    programs/page.tsx       # Center programs & events
    newsletter/page.tsx     # Opt-in signup + confirm + unsubscribe
    appointments/page.tsx   # Appointment requests (Dr. Roberts)
    dashboard/page.tsx      # Staff dashboard, charts, reports
    login/page.tsx, register/page.tsx
    layout.tsx, globals.css # Cornell Bowers palette
  components/               # Header, Charts (hand-rolled SVG)
  lib/api.ts                # Typed API client
```

## Design Decisions

- **It belongs to the Center, so it looks like the Center.** Design
  follows bowers.cornell.edu Belonging at Bowers: carnelian red `#B31B1B`
  dominant, dark navy `#000056`, light background `#F7F7F7`, near-black
  text `#2A2A2A`, orange accent `#F8981D`, system-sans stack (TT Commons
  Pro is licensed, so a close system fallback is used). The October
  build's invented dark-green palette was retired. Clean institutional
  Cornell look: white background, carnelian headers/accents, dark text,
  gray borders.
- **Real content or nothing.** Every resource, conference, and program in
  the seed is traceable to the two Bowers pages jem linked or to her own
  words (`REAL-SPEC.md` §7). Nothing is invented: no fake testimonials,
  no invented student names, no invented events or dates, no invented
  resource descriptions. Where a date is unknown it is stored null and
  shown as such. Grace Hopper Celebration 2026 is listed as cancelled,
  never as upcoming.
- **Real users over impressive stack.** The chat's settled stack
  (Next.js + TypeScript + FastAPI + PostgreSQL) is kept exactly; the
  deploy target the chat named (Railway) is swapped for Render because
  that is the working deploy path for jem's other projects. One Docker
  service serves API + static frontend — no second service, no cache
  layer, no background jobs. A working tool the Center can actually use
  beats a flashier architecture.
- **The newsletter is the core feature (Nov 20, 2026).** jem: the
  newsletter should be the core because it sends the resources to
  students at the Cornell domain. So the homepage leads with it (hero:
  "Welcome — the Center's resources and opportunities, in your
  inbox", signup prompt in the hero, what subscribers get below it),
  nav puts Newsletter first, and the campaign composer is reframed as
  composing a newsletter issue: staff pick resources from the
  platform's real resource list to feature, write the message, and
  send to subscribers and/or an audience. Confirmation arrives by
  email: signup sends a confirmation email addressed by name with
  the confirm link (the channel — no on-page link when SMTP is
  configured); when no mail server is configured, the link appears
  on /newsletter only, labeled as a temporary fallback, and the
  homepage shows just a short note. Emails send from
  `writesaifreewalter@gmail.com` (SMTP_USER and SMTP_FROM) via
  Gmail SMTP — the app password is set in the Render dashboard, never
  in any file. Sub-routes serve their own pages (not the homepage
  fallback) and HTML is served no-cache so a redeploy shows
  immediately. Public
  signup accepts `@cornell.edu` addresses only, validated backend and
  frontend ("Use your Cornell email to subscribe"); double opt-in
  stays. Staff-imported org contacts are vetted by staff, not
  domain-checked — but they should be Cornell students, since the
  newsletter goes to the Cornell domain. The org audiences feed the
  newsletter; they are not a separate channel from it.
- **Reach is the feature — core-first reframe (Nov 10, 2026).** jem
  reviewed the Nov 6 rebuild and said the core functionality and goal
  were missing: a resource listing with a signup form is not the
  platform. The platform's job is reach — the Center reaching the
  students who need it — so the build is now organized around three
  core features, and the homepage leads with them: (1) **the
  newsletter** — issues built from the Center's real resources, sent
  to students at the Cornell domain (see the bullet above);
  (2) **audience intake from orgs** — staff take in who to reach by
  CSV upload, manual add, or an org representative's submission, which
  lands as pending review and is never auto-added; (3) **real
  appointment booking** — staff add Dr. Roberts' availability as slots
  and visitors book an open one. Resources and conferences remain, but
  they are not the lead.
- **Org lists only with agreement — the platform provides the intake,
  it does not take lists.** The Nov 6 rule ("never hold a roster taken
  from URMC, NSBE, or CampusGroups") was the honest reading of an
  unsettled question; jem's core requirement is that the platform take
  in who to reach. The resolved position: orgs share their lists with
  their agreement, submissions are pending review until staff approve
  them, and the permission note is stated in the UI and in
  `DEPLOY_NOTES.md`. No org contacts, rosters, or agreements were
  invented — zero contacts are seeded, and slots start empty until an
  admin adds them.
- **Honest data, going forward.** Participation, subscribers, audiences,
  contacts, campaigns, slots, and bookings start empty and are tracked
  from now on. The dashboard charts only real DB rows — an empty chart
  is honest, a fabricated trend line would not be. The 100+ students
  served, 3 initiatives, 2 departments, 100+ stakeholders, 40%
  utilization increase, and $4,000 budget are program-impact numbers
  from jem's own record, shown labeled as such on the home page, not
  charted as fake time series.
- **Auth is deliberately simple and documented as open.** Email/password
  with PBKDF2 hashing (stdlib only), DB session tokens, roles
  student/faculty/admin; registration always creates a student and an
  admin promotes staff. The login method (Cornell NetID/SSO vs email
  allowlist vs open) is still an open question for jem and the Center —
  the simple flow is a placeholder that can be swapped, not a decision
  smuggled in.
- **No mail server yet, by design — and nothing is faked as "sent".**
  Campaigns send through SMTP configured with `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` (Gmail app password
  or SendGrid — see `DEPLOY_NOTES.md`). While those are unset, a send
  saves the campaign as "ready to send" (`status=queued`) with its full
  content and recipient list visible. Newsletter signup sends a
  confirmation email when SMTP is configured; while it is unset, the
  confirmation link appears on /newsletter only, labeled as a
  temporary fallback. Nothing is faked as "sent".
- **SQLite default, Postgres escape hatch.** SQLite keeps local
  verification and the free deploy zero-setup; the same models run on
  Postgres via `DATABASE_URL`, which is the production shape. The
  tradeoff (ephemeral container storage) is documented in
  `DEPLOY_NOTES.md`, not hidden.
