"""Bowers D&I Platform API — Center for Belonging, Cornell CIS Bowers.

FastAPI + SQLAlchemy. Postgres when DATABASE_URL is set, SQLite file
fallback (./bowers.db) when unset.

Auth: stdlib-only (hashlib.pbkdf2_hmac passwords, secrets.token_urlsafe
session tokens, 7-day expiry, Bearer auth). Roles: student, faculty,
admin. Registration always creates role "student"; an admin promotes
roles via PATCH /api/auth/users/{id}/role.

On startup the tables are created and seeded with the real content from
REAL-SPEC.md §7.1 when empty (see app/seed.py). Participation,
subscribers, appointments, and outreach are tracked going forward only.

If a built frontend exists at ../frontend/out (relative to backend/),
it is served statically with an SPA fallback to index.html for
non-/api paths.
"""

import json
import os
import secrets
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import auth, models, schemas, seed
from .database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed.seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Bowers D&I Platform API", lifespan=lifespan)

_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_frontend_url = os.environ.get("FRONTEND_URL")
if _frontend_url:
    _origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user_out(user: models.User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --------------------------------- Auth ----------------------------------


@app.post("/api/auth/register", status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if payload.role is not None and payload.role != "student":
        raise HTTPException(
            status_code=400,
            detail="Registration always creates role 'student'; "
            "an admin promotes roles afterwards.",
        )
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )
    existing = (
        db.query(models.User).filter(models.User.email == payload.email).first()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")
    salt = auth.new_salt()
    user = models.User(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        password_hash=auth.hash_password(payload.password, salt),
        salt=salt.hex(),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth.create_session(db, user)
    return {"token": token.token, "user": _user_out(user)}


@app.post("/api/auth/login")
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.email == payload.email.strip().lower())
        .first()
    )
    if user is None or not auth.verify_password(
        payload.password, user.salt, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_session(db, user)
    return {"token": token.token, "user": _user_out(user)}


@app.get("/api/auth/me")
def me(user: models.User = Depends(auth.get_current_user)):
    return _user_out(user)


@app.get("/api/auth/users")
def list_users(admin: models.User = Depends(auth.require_admin),
               db: Session = Depends(get_db)):
    return [_user_out(u) for u in db.query(models.User).order_by(models.User.id)]


@app.patch("/api/auth/users/{user_id}/role")
def set_role(
    user_id: int,
    payload: schemas.RoleUpdate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return _user_out(user)


# ------------------------------- Resources -------------------------------


@app.get("/api/resources", response_model=list[schemas.ResourceOut])
def list_resources(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    audience: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Resource)
    if search:
        like = f"%{search}%"
        query = query.filter(
            models.Resource.title.ilike(like)
            | models.Resource.description.ilike(like)
        )
    if category:
        query = query.filter(models.Resource.category == category)
    if audience:
        query = query.filter(models.Resource.audience == audience)
    return query.order_by(models.Resource.title).all()


@app.post("/api/resources", response_model=schemas.ResourceOut, status_code=201)
def create_resource(
    payload: schemas.ResourceCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = models.Resource(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/resources/{resource_id}", response_model=schemas.ResourceOut)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Resource, resource_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return row


# ------------------------------ Conferences ------------------------------


@app.get("/api/conferences", response_model=list[schemas.ConferenceOut])
def list_conferences(
    upcoming: bool = Query(default=False),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Conference)
    if upcoming:
        query = query.filter(models.Conference.status == "upcoming")
    if status:
        query = query.filter(models.Conference.status == status)
    return query.order_by(models.Conference.date).all()


@app.post("/api/conferences", response_model=schemas.ConferenceOut, status_code=201)
def create_conference(
    payload: schemas.ConferenceCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = models.Conference(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/conferences/{conference_id}", response_model=schemas.ConferenceOut)
def get_conference(conference_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Conference, conference_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conference not found")
    return row


@app.get(
    "/api/conferences/{conference_id}/participation",
    response_model=list[schemas.ParticipationOut],
)
def list_participation(
    conference_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if db.get(models.Conference, conference_id) is None:
        raise HTTPException(status_code=404, detail="Conference not found")
    return (
        db.query(models.ConferenceParticipation)
        .filter(models.ConferenceParticipation.conference_id == conference_id)
        .order_by(models.ConferenceParticipation.created_at)
        .all()
    )


@app.post(
    "/api/conferences/{conference_id}/participation",
    response_model=schemas.ParticipationOut,
    status_code=201,
)
def add_participation(
    conference_id: int,
    payload: schemas.ParticipationCreate,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if db.get(models.Conference, conference_id) is None:
        raise HTTPException(status_code=404, detail="Conference not found")
    target_user_id = user.id
    if payload.user_id is not None:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only an admin can record participation for another user",
            )
        if db.get(models.User, payload.user_id) is None:
            raise HTTPException(status_code=404, detail="User not found")
        target_user_id = payload.user_id
    row = models.ConferenceParticipation(
        conference_id=conference_id,
        user_id=target_user_id,
        note=payload.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --------------------------------- Events ---------------------------------


@app.get("/api/events", response_model=list[schemas.EventOut])
def list_events(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Event)
    if category:
        query = query.filter(models.Event.category == category)
    return query.order_by(models.Event.name).all()


@app.post("/api/events", response_model=schemas.EventOut, status_code=201)
def create_event(
    payload: schemas.EventCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = models.Event(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ------------------------------ Newsletter -------------------------------
# Double opt-in. NOTE: there is no mail server wired up here, so the
# confirmation link is returned in the signup response and shown on the
# signup confirmation page. Wiring SendGrid / an SMTP service would let
# the link be emailed instead (see DEPLOY_NOTES.md).


def _confirmation_url(request: Request, token: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/newsletter/confirm?token={token}"


def _subscriber_out(row: models.NewsletterSubscriber) -> dict:
    def _parse(raw: str) -> list:
        try:
            parsed = json.loads(raw or "[]")
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "interests": _parse(row.interests),
        "topics": _parse(row.topics),
        "source": row.source,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@app.post("/api/newsletter/signup")
def newsletter_signup(
    payload: schemas.NewsletterSignup,
    request: Request,
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required")
    row = (
        db.query(models.NewsletterSubscriber)
        .filter(models.NewsletterSubscriber.email == email)
        .first()
    )
    if row is not None and row.status == "confirmed":
        return JSONResponse(
            status_code=200, content={"ok": True, "already_subscribed": True}
        )
    token = secrets.token_urlsafe(32)
    if row is None:
        row = models.NewsletterSubscriber(
            name=payload.name.strip(),
            email=email,
            interests=json.dumps(payload.interests),
            topics=json.dumps(payload.topics),
            source=payload.source,
            status="pending",
            confirmation_token=token,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return JSONResponse(
            status_code=201,
            content={
                "ok": True,
                "confirmation_token": token,
                "confirmation_url": _confirmation_url(request, token),
            },
        )
    # Pending (or previously unsubscribed): re-issue a fresh token.
    row.name = payload.name.strip() or row.name
    row.interests = json.dumps(payload.interests)
    row.topics = json.dumps(payload.topics)
    row.source = payload.source or row.source
    row.status = "pending"
    row.confirmation_token = token
    db.commit()
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "confirmation_token": token,
            "confirmation_url": _confirmation_url(request, token),
        },
    )


@app.get("/api/newsletter/confirm")
def newsletter_confirm(token: str = Query(default=""), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=400, detail="Confirmation token required")
    row = (
        db.query(models.NewsletterSubscriber)
        .filter(models.NewsletterSubscriber.confirmation_token == token)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid confirmation token")
    row.status = "confirmed"
    row.confirmation_token = None
    db.commit()
    return {"ok": True, "email": row.email}


@app.post("/api/newsletter/unsubscribe")
def newsletter_unsubscribe(
    payload: schemas.NewsletterUnsubscribe, db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()
    row = (
        db.query(models.NewsletterSubscriber)
        .filter(models.NewsletterSubscriber.email == email)
        .first()
    )
    if row is not None:
        row.status = "unsubscribed"
        db.commit()
    return {"ok": True}


@app.get("/api/newsletter/subscribers")
def list_subscribers(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.NewsletterSubscriber)
        .order_by(models.NewsletterSubscriber.created_at.desc())
        .all()
    )
    return [_subscriber_out(r) for r in rows]


# ----------------------------- Appointments ------------------------------


@app.post("/api/appointments", status_code=201)
def create_appointment(
    payload: schemas.AppointmentCreate, db: Session = Depends(get_db)
):
    row = models.Appointment(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        topic=payload.topic,
        preferred_date=payload.preferred_date,
        preferred_time=payload.preferred_time,
        notes=payload.notes,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "topic": row.topic,
        "preferred_date": row.preferred_date.isoformat()
        if row.preferred_date
        else None,
        "preferred_time": row.preferred_time,
        "notes": row.notes,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@app.get("/api/appointments", response_model=list[schemas.AppointmentOut])
def list_appointments(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Appointment)
        .order_by(models.Appointment.created_at.desc())
        .all()
    )


@app.patch("/api/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    payload: schemas.AppointmentStatusUpdate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Appointment, appointment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    row.status = payload.status
    db.commit()
    db.refresh(row)
    return row


# ------------------------------- Outreach --------------------------------


@app.get("/api/outreach", response_model=list[schemas.OutreachOut])
def list_outreach(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.OutreachEntry)
        .order_by(models.OutreachEntry.date.desc())
        .all()
    )


@app.post("/api/outreach", response_model=schemas.OutreachOut, status_code=201)
def create_outreach(
    payload: schemas.OutreachCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = models.OutreachEntry(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/outreach/stats", response_model=schemas.OutreachStats)
def outreach_stats(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    total_entries = db.query(func.count(models.OutreachEntry.id)).scalar() or 0
    total_contacts = (
        db.query(func.coalesce(func.sum(models.OutreachEntry.contacts_reached), 0)).scalar()
        or 0
    )
    by_program = (
        db.query(
            models.OutreachEntry.program,
            func.count(models.OutreachEntry.id).label("entries"),
            func.coalesce(func.sum(models.OutreachEntry.contacts_reached), 0).label(
                "contacts"
            ),
        )
        .group_by(models.OutreachEntry.program)
        .order_by(func.sum(models.OutreachEntry.contacts_reached).desc())
        .all()
    )
    return {
        "total_entries": total_entries,
        "total_contacts": total_contacts,
        "by_program": [
            {"program": p, "entries": e, "contacts": c} for p, e, c in by_program
        ],
    }


# --------------------------- Dashboard / reports -------------------------
# Everything here is computed from REAL database rows only. No fabricated
# series, no placeholder numbers: an empty table contributes zero.


def _dashboard_data(db: Session) -> dict:
    subscribers = db.query(models.NewsletterSubscriber).all()
    appointments = db.query(models.Appointment).all()
    outreach = db.query(models.OutreachEntry).all()
    conferences = db.query(models.Conference).order_by(models.Conference.id).all()
    participation = db.query(models.ConferenceParticipation).all()

    totals = {
        "subscribers": len(subscribers),
        "confirmed_subscribers": sum(
            1 for s in subscribers if s.status == "confirmed"
        ),
        "appointments_pending": sum(
            1 for a in appointments if a.status == "pending"
        ),
        "resources": db.query(func.count(models.Resource.id)).scalar() or 0,
        "conferences": len(conferences),
        "events": db.query(func.count(models.Event.id)).scalar() or 0,
        "participation_total": len(participation),
        "outreach_contacts": sum(o.contacts_reached for o in outreach),
    }

    counts_by_conf = Counter(p.conference_id for p in participation)
    participation_by_conference = [
        {"conference": c.name, "count": counts_by_conf.get(c.id, 0)}
        for c in conferences
    ]

    by_month: dict[str, dict] = defaultdict(lambda: {"contacts": 0, "entries": 0})
    for o in outreach:
        m = o.date.strftime("%Y-%m")
        by_month[m]["contacts"] += o.contacts_reached
        by_month[m]["entries"] += 1
    outreach_by_month = [
        {"month": m, "contacts": v["contacts"], "entries": v["entries"]}
        for m, v in sorted(by_month.items())
    ]

    sub_months = Counter(
        s.created_at.strftime("%Y-%m") for s in subscribers if s.created_at
    )
    subscribers_by_month = [
        {"month": m, "count": c} for m, c in sorted(sub_months.items())
    ]

    appt_status = Counter(a.status for a in appointments)
    appointments_by_status = {
        s: appt_status.get(s, 0)
        for s in ("pending", "confirmed", "declined", "completed")
    }

    return {
        "totals": totals,
        "participation_by_conference": participation_by_conference,
        "outreach_by_month": outreach_by_month,
        "subscribers_by_month": subscribers_by_month,
        "appointments_by_status": appointments_by_status,
    }


@app.get("/api/dashboard")
def dashboard(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return _dashboard_data(db)


@app.get("/api/reports/summary")
def reports_summary(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    data = _dashboard_data(db)
    outreach = db.query(models.OutreachEntry).all()
    by_program: dict[str, dict] = defaultdict(lambda: {"entries": 0, "contacts": 0})
    for o in outreach:
        by_program[o.program]["entries"] += 1
        by_program[o.program]["contacts"] += o.contacts_reached
    pending = (
        db.query(models.Appointment)
        .filter(models.Appointment.status == "pending")
        .order_by(models.Appointment.created_at)
        .all()
    )
    return {
        "totals": data["totals"],
        "participation_by_conference": data["participation_by_conference"],
        "outreach": {
            "total_entries": len(outreach),
            "total_contacts": data["totals"]["outreach_contacts"],
            "by_program": [
                {"program": p, **v} for p, v in sorted(by_program.items())
            ],
        },
        "subscriber_growth": data["subscribers_by_month"],
        "open_appointments": {
            "count": len(pending),
            "appointments": [
                {
                    "id": a.id,
                    "name": a.name,
                    "email": a.email,
                    "topic": a.topic,
                    "preferred_date": a.preferred_date.isoformat()
                    if a.preferred_date
                    else None,
                    "preferred_time": a.preferred_time,
                    "created_at": a.created_at.isoformat()
                    if a.created_at
                    else None,
                }
                for a in pending
            ],
        },
        "appointments_by_status": data["appointments_by_status"],
    }


# ------------------------- Static frontend (SPA) -------------------------
# Only active when a built frontend exists at ../frontend/out. API routes
# above always win; anything else serves the built file or index.html.

if FRONTEND_DIR.is_dir():

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")
