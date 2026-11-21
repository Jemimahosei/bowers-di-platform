# Bowers D&I Platform

## 🔗 Live site: https://bowers-di-platform.onrender.com

The working platform for the Center for Belonging at Cornell Bowers CIS (College of Computing and Information Science). Its core job is reach: getting the Center's resources to the students who need them. The newsletter is the core feature — students sign up with a Cornell email, confirm by email (double opt-in), and receive issues built from the Center's real resources, sent to subscriber and audience segments. Staff also take in audiences from student orgs (submissions stay pending review until approved) and visitors book real appointment slots with Dr. LeeAnn Roberts, Director of the DEIB office. Around that core: searchable resource discovery, conference participation tracking, programs and events, and a staff dashboard.

## Architecture

```
Browser ──▶ Next.js (React + TypeScript, static export)
              │  /api/*
              ▼
           FastAPI (Python, uvicorn)
              │  reads / writes
              ▼
           SQLite (bowers.db) ◀── PostgreSQL via DATABASE_URL
```

- **Frontend** (Next.js 15, static export): home, resources, conferences, programs, newsletter signup, appointments, staff dashboard. The backend serves the built export, so the site and API run on one URL.
- **Backend** (FastAPI + SQLAlchemy): auth with roles (student/faculty/admin), resources, conferences, events, newsletter signup/confirm/unsubscribe, audiences, campaigns, availability slots and bookings, outreach log, dashboard aggregates (`/api/health`, `/api/resources`, `/api/newsletter/signup`, `/api/appointments`, `/api/campaigns`, `/api/dashboard`).
- **Email** (stdlib `smtplib`, no extra service): confirmation emails and campaign sends go through SMTP configured with `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`. No mail server is configured on the live deploy, so campaigns stay saved as "ready to send" and the confirmation link appears on the newsletter page as a labeled fallback — nothing is ever claimed sent when it was not.
- **Deploy**: one Docker service on Render (`render.yaml`, health check `/api/health`) that builds the frontend and serves it from the backend.

## Stack

Next.js 15 · React 19 · TypeScript · FastAPI · SQLAlchemy · SQLite / PostgreSQL · Docker · Render

## Run it locally

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 — it serves the API and, once built (`cd frontend && npm install && npm run build`), the site. For frontend dev: `cd frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev` → http://localhost:3000. Or `docker compose up --build` for Postgres + API + web.

## Tests

Backend verification suite (`backend/verify_backend.py`) boots its own server on a throwaway SQLite database and checks every endpoint family — auth and roles, resources, newsletter signup/confirm, campaigns, slots and bookings, dashboard — printing PASS/FAIL per check.

## Notes

- The live site is on Render's free tier, so the first load can take about a minute while it wakes up.
- The live deploy runs on SQLite with no `DATABASE_URL` set, so its data lives in the container's ephemeral filesystem: signups, subscribers, audiences, and bookings are wiped on redeploy. Set `DATABASE_URL` to a Postgres URL for persistent data.
- All seed content is the Center's real resources, conferences, and programs; participation, subscribers, audiences, and bookings start empty and are tracked from real use only.
