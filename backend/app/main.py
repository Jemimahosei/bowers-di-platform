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

import csv
import io
import json
import os
import secrets
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import auth, mail, models, schemas, seed
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
    return {"status": "ok", "email_mode": mail.email_mode(),
            "last_email_error": mail.last_error()}


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
# The newsletter is the CORE feature: it is how the Center's resources
# reach students at the Cornell domain. Public signup accepts Cornell
# addresses ONLY (@cornell.edu, validated here and on the frontend).
# Double opt-in. The confirmation email is the channel: signup sends
# it when email is configured (see mail.send_confirmation_email). When
# no email sender is configured, the signup response carries the token for the
# /newsletter-only fallback link instead (see DEPLOY_NOTES.md).


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
    if not mail.is_cornell_email(email):
        raise HTTPException(status_code=400, detail=mail.CORNELL_EMAIL_ERROR)
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
    status_code = 201
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
    else:
        # Pending (or previously unsubscribed): re-issue a fresh token.
        row.name = payload.name.strip() or row.name
        row.interests = json.dumps(payload.interests)
        row.topics = json.dumps(payload.topics)
        row.source = payload.source or row.source
        row.status = "pending"
        row.confirmation_token = token
        db.commit()
        status_code = 200
    confirmation_url = _confirmation_url(request, token)
    # The confirmation email is the channel: send it when email is
    # configured. When it is not configured (or sending fails), fall
    # back to returning the link for /newsletter only — never pretend
    # the email went out.
    email_sent = False
    if mail.email_configured():
        try:
            mail.send_confirmation_email(
                email, payload.name.strip(), confirmation_url)
            email_sent = True
        except Exception:
            email_sent = False
    if email_sent:
        return JSONResponse(
            status_code=status_code,
            content={"ok": True, "email_sent": True,
                     "email_configured": True},
        )
    return JSONResponse(
        status_code=status_code,
        content={"ok": True, "email_sent": False,
                 "email_configured": mail.email_configured(),
                 "confirmation_token": token,
                 "confirmation_url": confirmation_url},
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


# ------------------------- Slots & bookings ------------------------------
# Real appointment booking with Dr. LeeAnn Roberts (replaces the old
# request-form inbox). Slots start EMPTY — staff add Dr. Roberts'
# availability; a visitor books an open slot and it becomes BOOKED.
# Cancelling a booking re-opens the slot. Contact
# deib-office@bowers.cornell.edu stays visible in the UI.


def _slot_out(row: models.AvailabilitySlot) -> dict:
    return {
        "id": row.id,
        "date": row.date.isoformat() if row.date else None,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "type": row.type,
        "host": row.host,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _booking_out(row: models.Booking, db: Session) -> dict:
    slot = db.get(models.AvailabilitySlot, row.slot_id)
    return {
        "id": row.id,
        "slot_id": row.slot_id,
        "name": row.name,
        "email": row.email,
        "purpose": row.purpose,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "cancelled_at": row.cancelled_at.isoformat()
        if row.cancelled_at
        else None,
        "slot": _slot_out(slot) if slot is not None else None,
    }


@app.get("/api/slots")
def list_slots(
    open_only: bool = Query(default=True), db: Session = Depends(get_db)
):
    query = db.query(models.AvailabilitySlot)
    if open_only:
        query = query.filter(models.AvailabilitySlot.status == "open")
    return [
        _slot_out(s)
        for s in query.order_by(
            models.AvailabilitySlot.date, models.AvailabilitySlot.start_time
        ).all()
    ]


@app.post("/api/slots", status_code=201)
def create_slot(
    payload: schemas.SlotCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=400, detail="End time must be after start time"
        )
    row = models.AvailabilitySlot(
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        type=payload.type,
        host=payload.host,
        status="open",
        created_by=admin.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _slot_out(row)


@app.delete("/api/slots/{slot_id}")
def delete_slot(
    slot_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.AvailabilitySlot, slot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    if row.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Booked slots cannot be deleted — cancel the booking first",
        )
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.post("/api/slots/{slot_id}/book", status_code=201)
def book_slot(
    slot_id: int, payload: schemas.BookingCreate, db: Session = Depends(get_db)
):
    slot = db.get(models.AvailabilitySlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.status != "open":
        raise HTTPException(
            status_code=409, detail="That slot is no longer available"
        )
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    email = payload.email.strip().lower()
    if "@" not in email or not email.endswith("@cornell.edu"):
        raise HTTPException(
            status_code=400, detail="A Cornell email address is required"
        )
    row = models.Booking(
        slot_id=slot.id,
        name=payload.name.strip(),
        email=email,
        purpose=payload.purpose.strip(),
        status="booked",
    )
    slot.status = "booked"
    db.add(row)
    db.commit()
    db.refresh(row)
    if mail.email_configured():
        # The success copy promises a confirmation email — send it.
        # Non-fatal: a mail failure must never lose the booking.
        try:
            mail.send_booking_confirmation_email(
                email,
                row.name,
                f"{slot.date.isoformat()} at {slot.start_time}",
                slot.type,
                slot.host,
            )
        except Exception:  # noqa: BLE001 - booking already saved
            pass
    return _booking_out(row, db)


@app.get("/api/bookings")
def list_bookings(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return [
        _booking_out(b, db)
        for b in db.query(models.Booking)
        .order_by(models.Booking.created_at.desc())
        .all()
    ]


@app.post("/api/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Booking, booking_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if row.status == "cancelled":
        raise HTTPException(status_code=409, detail="Booking already cancelled")
    slot = db.get(models.AvailabilitySlot, row.slot_id)
    row.status = "cancelled"
    row.cancelled_at = datetime.utcnow()
    if slot is not None:
        slot.status = "open"
    db.commit()
    db.refresh(row)
    return _booking_out(row, db)


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


# ------------------ Core 1: audiences & contacts -----------------------
# The platform takes in who to reach. Org lists are shared WITH the
# org's agreement — the platform provides the intake, it does not take
# lists. Seed ZERO contacts: no roster exists.


def _parse_json_list(raw: str) -> list:
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _contact_out(row: models.Contact) -> dict:
    return {
        "id": row.id,
        "audience_id": row.audience_id,
        "name": row.name,
        "email": row.email,
        "source_org": row.source_org,
        "interests": _parse_json_list(row.interests),
        "tags": _parse_json_list(row.tags),
        "source": row.source,
        "opted_out": bool(row.opted_out),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _audience_out(row: models.Audience, db: Session) -> dict:
    total = (
        db.query(func.count(models.Contact.id))
        .filter(models.Contact.audience_id == row.id)
        .scalar()
        or 0
    )
    opted_out = (
        db.query(func.count(models.Contact.id))
        .filter(
            models.Contact.audience_id == row.id,
            models.Contact.opted_out == 1,
        )
        .scalar()
        or 0
    )
    return {
        "id": row.id,
        "name": row.name,
        "source_org": row.source_org,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "contact_count": total,
        "opted_out_count": opted_out,
    }


def _valid_email(email: str) -> bool:
    email = email.strip().lower()
    if not email or " " in email or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain


def _parse_contacts_csv(text: str, default_org: str = "") -> tuple[list, list]:
    """Parse a contacts CSV (columns: name, email, org, interests).

    Interests are separated by semicolons. Returns (valid_rows, errors)
    where each valid row is {name, email, source_org, interests} and each
    error is {row, reason}. Row numbers are 1-based data rows.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], [{"row": 0, "reason": "Empty file — expected a header row"}]
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    if "email" not in headers:
        return [], [{"row": 0, "reason": "Missing required column: email"}]
    email_key = headers["email"]
    name_key = headers.get("name")
    org_key = headers.get("org")
    interests_key = headers.get("interests")
    valid: list = []
    errors: list = []
    for i, raw in enumerate(reader, start=1):
        if raw is None:
            continue
        email = (raw.get(email_key) or "").strip().lower()
        if not email:
            if not any((v or "").strip() for v in raw.values()):
                continue  # blank line
            errors.append({"row": i, "reason": "Missing email"})
            continue
        if not _valid_email(email):
            errors.append({"row": i, "reason": f"Invalid email: {email}"})
            continue
        name = (raw.get(name_key) or "").strip() if name_key else ""
        org = (raw.get(org_key) or "").strip() if org_key else ""
        interests_raw = (
            (raw.get(interests_key) or "").strip() if interests_key else ""
        )
        interests = [
            part.strip() for part in interests_raw.split(";") if part.strip()
        ]
        valid.append(
            {
                "name": name,
                "email": email,
                "source_org": org or default_org,
                "interests": interests,
            }
        )
    return valid, errors


@app.post("/api/audiences", status_code=201)
def create_audience(
    payload: schemas.AudienceCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Audience name is required")
    row = models.Audience(
        name=payload.name.strip(),
        source_org=payload.source_org.strip(),
        description=payload.description.strip(),
        created_by=admin.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _audience_out(row, db)


@app.get("/api/audiences")
def list_audiences(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return [
        _audience_out(a, db)
        for a in db.query(models.Audience)
        .order_by(models.Audience.created_at.desc())
        .all()
    ]


@app.get("/api/audiences/{audience_id}")
def get_audience(
    audience_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Audience, audience_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Audience not found")
    out = _audience_out(row, db)
    out["contacts"] = [
        _contact_out(c)
        for c in db.query(models.Contact)
        .filter(models.Contact.audience_id == audience_id)
        .order_by(models.Contact.email)
        .all()
    ]
    return out


@app.post("/api/audiences/{audience_id}/contacts", status_code=201)
def add_contact(
    audience_id: int,
    payload: schemas.ContactCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    audience = db.get(models.Audience, audience_id)
    if audience is None:
        raise HTTPException(status_code=404, detail="Audience not found")
    email = payload.email.strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="A valid email is required")
    existing = (
        db.query(models.Contact)
        .filter(
            models.Contact.audience_id == audience_id,
            models.Contact.email == email,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="That email is already in this audience"
        )
    row = models.Contact(
        audience_id=audience_id,
        name=payload.name.strip(),
        email=email,
        source_org=payload.source_org.strip() or audience.source_org,
        interests=json.dumps(payload.interests),
        tags=json.dumps(payload.tags),
        source="manual",
        opted_out=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _contact_out(row)


@app.patch("/api/audiences/{audience_id}/contacts/{contact_id}")
def update_contact(
    audience_id: int,
    contact_id: int,
    payload: schemas.ContactUpdate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.Contact)
        .filter(
            models.Contact.id == contact_id,
            models.Contact.audience_id == audience_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.interests is not None:
        row.interests = json.dumps(payload.interests)
    if payload.tags is not None:
        row.tags = json.dumps(payload.tags)
    if payload.opted_out is not None:
        row.opted_out = 1 if payload.opted_out else 0
    db.commit()
    db.refresh(row)
    return _contact_out(row)


@app.delete("/api/audiences/{audience_id}/contacts/{contact_id}")
def delete_contact(
    audience_id: int,
    contact_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.Contact)
        .filter(
            models.Contact.id == contact_id,
            models.Contact.audience_id == audience_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/audiences/contacts/template")
def contacts_template(
    admin: models.User = Depends(auth.require_admin),
):
    return PlainTextResponse(
        "name,email,org,interests\n",
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=contacts-template.csv"
        },
    )


@app.post("/api/audiences/{audience_id}/contacts/upload")
async def upload_contacts(
    audience_id: int,
    file: UploadFile = File(...),
    preview: str = Form(default="false"),
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    audience = db.get(models.Audience, audience_id)
    if audience is None:
        raise HTTPException(status_code=404, detail="Audience not found")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File must be UTF-8 CSV text"
        )
    valid, errors = _parse_contacts_csv(text, default_org=audience.source_org)
    is_preview = preview.strip().lower() in {"true", "1", "yes"}
    if is_preview:
        return {
            "preview": True,
            "valid_rows": len(valid),
            "invalid_rows": len(errors),
            "errors": errors,
            "sample": valid[:5],
        }
    imported = 0
    skipped: list = list(errors)
    for entry in valid:
        existing = (
            db.query(models.Contact)
            .filter(
                models.Contact.audience_id == audience_id,
                models.Contact.email == entry["email"],
            )
            .first()
        )
        if existing is not None:
            skipped.append(
                {
                    "row": None,
                    "reason": f"Already in this audience: {entry['email']}",
                }
            )
            continue
        db.add(
            models.Contact(
                audience_id=audience_id,
                name=entry["name"],
                email=entry["email"],
                source_org=entry["source_org"],
                interests=json.dumps(entry["interests"]),
                tags="[]",
                source="upload",
                opted_out=0,
            )
        )
        imported += 1
    db.commit()
    return {
        "preview": False,
        "imported": imported,
        "skipped": len(skipped),
        "errors": skipped,
    }


# ---------------------- Org-rep submissions ------------------------------
# An org representative submits their group's contacts; submissions land
# as "pending review" and staff approve them into an audience — never
# auto-added.


def _submission_out(row: models.OrgSubmission) -> dict:
    return {
        "id": row.id,
        "org_name": row.org_name,
        "rep_name": row.rep_name,
        "rep_email": row.rep_email,
        "notes": row.notes,
        "contacts": _parse_json_list(row.contacts_json),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat()
        if row.reviewed_at
        else None,
    }


@app.post("/api/org-submissions", status_code=201)
async def create_org_submission(request: Request, db: Session = Depends(get_db)):
    ctype = request.headers.get("content-type", "")
    org_name = rep_name = rep_email = notes = ""
    contacts: list = []
    if "application/json" in ctype:
        try:
            payload = schemas.OrgSubmissionCreate(**(await request.json()))
        except Exception as exc:  # noqa: BLE001 - pydantic validation
            raise HTTPException(status_code=422, detail=str(exc))
        org_name, rep_name, rep_email, notes = (
            payload.org_name,
            payload.rep_name,
            payload.rep_email,
            payload.notes,
        )
        contacts = [
            {
                "name": c.name.strip(),
                "email": c.email.strip().lower(),
                "interests": c.interests,
            }
            for c in payload.contacts
        ]
    else:
        form = await request.form()
        org_name = str(form.get("org_name") or "").strip()
        rep_name = str(form.get("rep_name") or "").strip()
        rep_email = str(form.get("rep_email") or "").strip().lower()
        notes = str(form.get("notes") or "").strip()
        upload = form.get("contacts_file")
        if upload is not None and hasattr(upload, "read"):
            raw = await upload.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400, detail="File must be UTF-8 CSV text"
                )
            valid, _errors = _parse_contacts_csv(text, default_org=org_name)
            contacts = valid
    if not org_name:
        raise HTTPException(status_code=400, detail="Organization name is required")
    if not _valid_email(rep_email):
        raise HTTPException(
            status_code=400, detail="A valid representative email is required"
        )
    clean = [c for c in contacts if _valid_email(c.get("email", ""))]
    if not clean:
        raise HTTPException(
            status_code=400,
            detail="No valid contacts were submitted — check the emails",
        )
    row = models.OrgSubmission(
        org_name=org_name,
        rep_name=rep_name,
        rep_email=rep_email,
        notes=notes,
        contacts_json=json.dumps(clean),
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _submission_out(row)


@app.get("/api/org-submissions")
def list_org_submissions(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return [
        _submission_out(s)
        for s in db.query(models.OrgSubmission)
        .order_by(models.OrgSubmission.created_at.desc())
        .all()
    ]


@app.post("/api/org-submissions/{submission_id}/review")
def review_org_submission(
    submission_id: int,
    payload: schemas.OrgSubmissionReview,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.OrgSubmission, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if row.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Submission already {row.status}"
        )
    if payload.decision == "reject":
        row.status = "rejected"
        row.reviewed_by = admin.id
        row.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _submission_out(row)
    # Approve: add contacts to an existing audience or a new one named
    # after the org. Duplicates (same email already in that audience)
    # are skipped, never duplicated.
    audience = None
    if payload.audience_id is not None:
        audience = db.get(models.Audience, payload.audience_id)
        if audience is None:
            raise HTTPException(status_code=404, detail="Audience not found")
    else:
        audience = (
            db.query(models.Audience)
            .filter(models.Audience.name == row.org_name)
            .first()
        )
        if audience is None:
            audience = models.Audience(
                name=row.org_name,
                source_org=row.org_name,
                description=f"Contacts submitted by {row.org_name}.",
                created_by=admin.id,
            )
            db.add(audience)
            db.flush()
    added = 0
    for entry in _parse_json_list(row.contacts_json):
        email = (entry.get("email") or "").strip().lower()
        if not _valid_email(email):
            continue
        existing = (
            db.query(models.Contact)
            .filter(
                models.Contact.audience_id == audience.id,
                models.Contact.email == email,
            )
            .first()
        )
        if existing is not None:
            continue
        db.add(
            models.Contact(
                audience_id=audience.id,
                name=(entry.get("name") or "").strip(),
                email=email,
                source_org=row.org_name,
                interests=json.dumps(entry.get("interests") or []),
                tags="[]",
                source="org-submission",
                opted_out=0,
            )
        )
        added += 1
    row.status = "approved"
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    out = _submission_out(row)
    out["audience_id"] = audience.id
    out["contacts_added"] = added
    return out


# ------------------------- Core 2: campaigns -----------------------------
# Campaigns ARE the newsletter: staff compose an issue (subject +
# message) and pick resources from the platform's real resource list to
# feature in it; sending goes to confirmed newsletter subscribers
# and/or an audience segment. Preview renders the issue with the chosen
# resources and the exact recipient count (opted-out excluded).
# Sending needs an email sender (Resend via RESEND_API_KEY, or SMTP
# via SMTP_HOST/PORT/USER/PASS/FROM); without one the campaign is
# saved as "ready to send" (status "queued") with content +
# recipients visible — never claimed sent.


def _featured_resources(db: Session, campaign: models.Campaign) -> list:
    """The real resources featured in this issue, in stored order."""
    out = []
    for rid in _parse_json_list(campaign.resource_ids):
        row = db.get(models.Resource, rid)
        if row is None:
            continue
        out.append(
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "category": row.category,
                "audience": row.audience,
                "link": row.link,
            }
        )
    return out


def _issue_body(campaign: models.Campaign, db: Session) -> str:
    """The email body for a sent issue: the staff message plus the
    featured resources (title + link) appended."""
    body = campaign.body.rstrip()
    featured = _featured_resources(db, campaign)
    if not featured:
        return body
    lines = [body, "", "", "Featured resources from the Center:"]
    for r in featured:
        line = f"- {r['title']}"
        if r["link"]:
            line += f" — {r['link']}"
        lines.append(line)
        if r["description"]:
            lines.append(f"  {r['description']}")
    return "\n".join(lines)


def _validate_resource_ids(db: Session, resource_ids: list) -> None:
    for rid in resource_ids:
        if db.get(models.Resource, rid) is None:
            raise HTTPException(
                status_code=404, detail=f"Resource {rid} not found"
            )


def _campaign_recipients(db: Session, campaign: models.Campaign) -> list:
    """Compute the exact recipient list for a campaign, live.

    Contacts in the selected audiences (or all contacts when only an
    org filter is set), filtered by org and interest, with opted-out
    contacts excluded. Contacts contribute NOTHING when the issue
    targets subscribers only (no audience, no org filter) — a
    subscribers-only issue goes to subscribers alone. Optionally adds
    confirmed opt-in newsletter subscribers. Deduplicated by email.
    """
    try:
        audience_ids = [int(x) for x in json.loads(campaign.audience_ids or "[]")]
    except (json.JSONDecodeError, ValueError):
        audience_ids = []
    seen: dict[str, dict] = {}
    if audience_ids or campaign.org_filter:
        query = db.query(models.Contact).filter(models.Contact.opted_out == 0)
        if audience_ids:
            query = query.filter(models.Contact.audience_id.in_(audience_ids))
        if campaign.org_filter:
            query = query.filter(models.Contact.source_org == campaign.org_filter)
        for c in query.order_by(models.Contact.email).all():
            interests = _parse_json_list(c.interests) + _parse_json_list(c.tags)
            if campaign.interest_filter:
                needle = campaign.interest_filter.strip().lower()
                if not any(needle in i.lower() for i in interests):
                    continue
            key = c.email.strip().lower()
            if key not in seen:
                seen[key] = {"email": c.email, "name": c.name, "source": c.source}
    if campaign.include_self_signup:
        subs = (
            db.query(models.NewsletterSubscriber)
            .filter(models.NewsletterSubscriber.status == "confirmed")
            .all()
        )
        for s in subs:
            key = s.email.strip().lower()
            if key not in seen:
                seen[key] = {
                    "email": s.email,
                    "name": s.name,
                    "source": "self-signup",
                }
    return list(seen.values())


def _campaign_out(row: models.Campaign, db: Session) -> dict:
    stored = (
        db.query(func.count(models.CampaignRecipient.id))
        .filter(models.CampaignRecipient.campaign_id == row.id)
        .scalar()
        or 0
    )
    count = stored if stored else len(_campaign_recipients(db, row))
    return {
        "id": row.id,
        "subject": row.subject,
        "body": row.body,
        "sender_name": row.sender_name,
        "resource_ids": _parse_json_list(row.resource_ids),
        "featured_resources": _featured_resources(db, row),
        "audience_ids": _parse_json_list(row.audience_ids),
        "org_filter": row.org_filter,
        "interest_filter": row.interest_filter,
        "include_self_signup": bool(row.include_self_signup),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "error": row.error,
        "recipient_count": count,
    }


@app.post("/api/campaigns", status_code=201)
def create_campaign(
    payload: schemas.CampaignCreate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if not payload.subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Body is required")
    if (
        not payload.audience_ids
        and not payload.org_filter.strip()
        and not payload.include_self_signup
    ):
        raise HTTPException(
            status_code=400,
            detail="Select at least one audience, an organization filter, "
            "or newsletter subscribers",
        )
    _validate_resource_ids(db, payload.resource_ids)
    for audience_id in payload.audience_ids:
        if db.get(models.Audience, audience_id) is None:
            raise HTTPException(
                status_code=404, detail=f"Audience {audience_id} not found"
            )
    row = models.Campaign(
        subject=payload.subject.strip(),
        body=payload.body.strip(),
        sender_name=payload.sender_name.strip() or "Center for Belonging",
        resource_ids=json.dumps(payload.resource_ids),
        audience_ids=json.dumps(payload.audience_ids),
        org_filter=payload.org_filter.strip(),
        interest_filter=payload.interest_filter.strip(),
        include_self_signup=1 if payload.include_self_signup else 0,
        status="draft",
        created_by=admin.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _campaign_out(row, db)


@app.get("/api/campaigns")
def list_campaigns(
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return [
        _campaign_out(c, db)
        for c in db.query(models.Campaign)
        .order_by(models.Campaign.created_at.desc())
        .all()
    ]


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: int,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Campaign, campaign_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    out = _campaign_out(row, db)
    stored = (
        db.query(models.CampaignRecipient)
        .filter(models.CampaignRecipient.campaign_id == campaign_id)
        .order_by(models.CampaignRecipient.email)
        .all()
    )
    if stored:
        out["recipients"] = [
            {
                "email": r.email,
                "name": r.name,
                "source": r.source,
                "status": r.status,
                "error": r.error,
            }
            for r in stored
        ]
    else:
        out["recipients"] = _campaign_recipients(db, row)
    return out


@app.patch("/api/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int,
    payload: schemas.CampaignUpdate,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Campaign, campaign_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if row.status != "draft":
        raise HTTPException(
            status_code=409, detail="Only draft campaigns can be edited"
        )
    if payload.subject is not None:
        row.subject = payload.subject.strip()
    if payload.body is not None:
        row.body = payload.body.strip()
    if payload.sender_name is not None:
        row.sender_name = payload.sender_name.strip() or "Center for Belonging"
    if payload.resource_ids is not None:
        _validate_resource_ids(db, payload.resource_ids)
        row.resource_ids = json.dumps(payload.resource_ids)
    if payload.audience_ids is not None:
        for audience_id in payload.audience_ids:
            if db.get(models.Audience, audience_id) is None:
                raise HTTPException(
                    status_code=404, detail=f"Audience {audience_id} not found"
                )
        row.audience_ids = json.dumps(payload.audience_ids)
    if payload.org_filter is not None:
        row.org_filter = payload.org_filter.strip()
    if payload.interest_filter is not None:
        row.interest_filter = payload.interest_filter.strip()
    if payload.include_self_signup is not None:
        row.include_self_signup = 1 if payload.include_self_signup else 0
    if not row.subject or not row.body:
        raise HTTPException(status_code=400, detail="Subject and body are required")
    if (
        not _parse_json_list(row.audience_ids)
        and not row.org_filter
        and not row.include_self_signup
    ):
        raise HTTPException(
            status_code=400,
            detail="Select at least one audience, an organization filter, "
            "or newsletter subscribers",
        )
    db.commit()
    db.refresh(row)
    return _campaign_out(row, db)


@app.post("/api/campaigns/{campaign_id}/send")
def send_campaign(
    campaign_id: int,
    request: Request,
    admin: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(models.Campaign, campaign_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if row.status == "sent":
        raise HTTPException(status_code=409, detail="Campaign already sent")
    recipients = _campaign_recipients(db, row)
    if not recipients:
        raise HTTPException(
            status_code=400, detail="No recipients match this campaign"
        )
    # Materialize per-recipient rows (queued) exactly once.
    existing = {
        r.email.lower()
        for r in db.query(models.CampaignRecipient)
        .filter(models.CampaignRecipient.campaign_id == campaign_id)
        .all()
    }
    for r in recipients:
        if r["email"].lower() not in existing:
            db.add(
                models.CampaignRecipient(
                    campaign_id=campaign_id,
                    email=r["email"],
                    name=r["name"],
                    source=r["source"],
                    status="queued",
                )
            )
    db.commit()
    if not mail.email_configured():
        # No email sender: the campaign is ready to send, with content and
        # recipients visible — but nothing is claimed sent.
        row.status = "queued"
        db.commit()
        db.refresh(row)
        return {
            **_campaign_out(row, db),
            "email_configured": False,
            "message": "No email configured — campaign saved as ready to send. "
            "Set RESEND_API_KEY and RESEND_FROM to send (see DEPLOY_NOTES.md).",
        }
    base = (os.environ.get("FRONTEND_URL") or str(request.base_url)).rstrip("/")
    queued = (
        db.query(models.CampaignRecipient)
        .filter(
            models.CampaignRecipient.campaign_id == campaign_id,
            models.CampaignRecipient.status == "queued",
        )
        .all()
    )
    sent = failed = 0
    issue_body = _issue_body(row, db)
    for recipient in queued:
        try:
            mail.send_email(
                recipient.email,
                row.subject,
                issue_body,
                row.sender_name,
                f"{base}/unsubscribe?email={recipient.email}",
            )
            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            recipient.error = ""
            sent += 1
        except Exception as exc:  # noqa: BLE001 - record per-recipient
            recipient.status = "failed"
            recipient.error = str(exc)
            failed += 1
    row.status = "sent" if failed == 0 else "partially_sent"
    row.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return {
        **_campaign_out(row, db),
        "email_configured": True,
        "sent": sent,
        "failed": failed,
    }


# --------------------------- Dashboard / reports -------------------------
# Everything here is computed from REAL database rows only. No fabricated
# series, no placeholder numbers: an empty table contributes zero.


def _dashboard_data(db: Session) -> dict:
    subscribers = db.query(models.NewsletterSubscriber).all()
    outreach = db.query(models.OutreachEntry).all()
    conferences = db.query(models.Conference).order_by(models.Conference.id).all()
    participation = db.query(models.ConferenceParticipation).all()
    slots = db.query(models.AvailabilitySlot).all()
    bookings = db.query(models.Booking).all()
    campaigns = db.query(models.Campaign).all()

    totals = {
        "subscribers": len(subscribers),
        "confirmed_subscribers": sum(
            1 for s in subscribers if s.status == "confirmed"
        ),
        "audiences": db.query(func.count(models.Audience.id)).scalar() or 0,
        "contacts": db.query(func.count(models.Contact.id)).scalar() or 0,
        "opted_out_contacts": (
            db.query(func.count(models.Contact.id))
            .filter(models.Contact.opted_out == 1)
            .scalar()
            or 0
        ),
        "campaigns": len(campaigns),
        "campaigns_sent": sum(
            1 for c in campaigns if c.status in {"sent", "partially_sent"}
        ),
        "open_slots": sum(1 for s in slots if s.status == "open"),
        "upcoming_bookings": sum(
            1
            for b in bookings
            if b.status == "booked"
            and db.get(models.AvailabilitySlot, b.slot_id) is not None
            and db.get(models.AvailabilitySlot, b.slot_id).date >= date.today()
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

    booking_status = Counter(b.status for b in bookings)
    bookings_by_status = {
        s: booking_status.get(s, 0) for s in ("booked", "cancelled")
    }
    slot_status = Counter(s.status for s in slots)
    slots_by_status = {s: slot_status.get(s, 0) for s in ("open", "booked")}
    campaign_status = Counter(c.status for c in campaigns)
    campaigns_by_status = {
        s: campaign_status.get(s, 0)
        for s in ("draft", "queued", "sent", "partially_sent")
    }

    return {
        "totals": totals,
        "participation_by_conference": participation_by_conference,
        "outreach_by_month": outreach_by_month,
        "subscribers_by_month": subscribers_by_month,
        "bookings_by_status": bookings_by_status,
        "slots_by_status": slots_by_status,
        "campaigns_by_status": campaigns_by_status,
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
        db.query(models.Booking)
        .filter(models.Booking.status == "booked")
        .order_by(models.Booking.created_at)
        .all()
    )
    upcoming = []
    for b in pending:
        slot = db.get(models.AvailabilitySlot, b.slot_id)
        if slot is None or slot.date < date.today():
            continue
        upcoming.append(
            {
                "id": b.id,
                "name": b.name,
                "email": b.email,
                "purpose": b.purpose,
                "date": slot.date.isoformat(),
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "type": slot.type,
                "host": slot.host,
                "created_at": b.created_at.isoformat()
                if b.created_at
                else None,
            }
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
        "open_bookings": {
            "count": len(upcoming),
            "bookings": upcoming,
        },
        "bookings_by_status": data["bookings_by_status"],
        "slots_by_status": data["slots_by_status"],
        "campaigns_by_status": data["campaigns_by_status"],
        "audiences": [
            _audience_out(a, db)
            for a in db.query(models.Audience)
            .order_by(models.Audience.created_at.desc())
            .all()
        ],
        "campaigns": [
            _campaign_out(c, db)
            for c in db.query(models.Campaign)
            .order_by(models.Campaign.created_at.desc())
            .all()
        ],
    }


# ------------------------- Static frontend (SPA) -------------------------
# Only active when a built frontend exists at ../frontend/out. API routes
# above always win; anything else serves the built file or index.html.

def _serve_file(path: Path) -> FileResponse:
    # HTML is the app shell: never let a browser or edge cache serve a
    # stale copy after a redeploy — the browser must revalidate every
    # load, so the new pages show immediately. Hashed JS/CSS under
    # /_next/static keep their default caching.
    if path.suffix == ".html":
        return FileResponse(path, headers={"Cache-Control": "no-cache"})
    return FileResponse(path)


if FRONTEND_DIR.is_dir():

    @app.get("/")
    def serve_index():
        return _serve_file(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return _serve_file(candidate)
        # Next.js static export (trailingSlash) puts each route in its
        # own directory with an index.html — /appointments must serve
        # appointments/index.html, not the root homepage. Without this
        # every extensionless sub-route fell through to the homepage.
        if candidate.is_dir():
            index = candidate / "index.html"
            if index.is_file():
                return _serve_file(index)
        return _serve_file(FRONTEND_DIR / "index.html")
