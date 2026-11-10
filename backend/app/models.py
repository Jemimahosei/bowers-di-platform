"""SQLAlchemy models for the Bowers D&I Platform (Center for Belonging,
Cornell CIS Bowers).

Content rules: no invented people, programs, or figures. Seed data lives
in seed.py and contains only the real items verified in REAL-SPEC.md §7.1.
Participation, subscribers, appointments, and outreach rows are tracked
going forward only — the seed creates none of them.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    """A platform user. Roles: student, faculty, admin.

    Registration always creates role "student"; an admin promotes roles.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, unique=True, index=True)
    # Hex-encoded hashlib.pbkdf2_hmac digest; see app/auth.py.
    password_hash = Column(String(256), nullable=False)
    # Hex-encoded per-user salt.
    salt = Column(String(64), nullable=False)
    role = Column(String(20), nullable=False, default="student", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SessionToken(Base):
    """A bearer session token with a 7-day expiry."""

    __tablename__ = "session_tokens"

    token = Column(String(128), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)


class Resource(Base):
    """A resource surfaced to students (office service, community
    resource, or campus partner)."""

    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    audience = Column(String(200), nullable=False, index=True)
    link = Column(String(500), nullable=False, default="")


class Conference(Base):
    """A conference / flagship program (Tapia, Code Afrique, Grace Hopper).

    ``status`` is one of: upcoming | past | cancelled | tba.
    ``attendees`` is an aggregate headcount when known, else null — never
    an invented number.
    """

    __tablename__ = "conferences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=True, index=True)
    end_date = Column(Date, nullable=True)
    location = Column(String(200), nullable=False, default="")
    status = Column(String(20), nullable=False, default="upcoming", index=True)
    description = Column(Text, nullable=False, default="")
    link = Column(String(500), nullable=False, default="")
    attendees = Column(Integer, nullable=True)


class ConferenceParticipation(Base):
    """One person's recorded attendance at one conference.

    Per-student participation, tracked going forward only. No roster
    exists historically, so the seed creates no rows here.
    """

    __tablename__ = "conference_participation"

    id = Column(Integer, primary_key=True, index=True)
    conference_id = Column(
        Integer, ForeignKey("conferences.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Event(Base):
    """A Center event/program (info session, workshop, program, community
    event). ``category`` is one of: program | conference | workshop |
    community. Dates are null unless a real date is known — never invented.
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    date = Column(Date, nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    category = Column(String(20), nullable=False, default="program", index=True)
    location = Column(String(200), nullable=True)


class NewsletterSubscriber(Base):
    """An opt-in newsletter subscriber (double opt-in).

    ``status`` is one of: pending | confirmed | unsubscribed.
    ``interests`` / ``topics`` are stored as JSON arrays in text columns.
    """

    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, default="")
    email = Column(String(320), nullable=False, unique=True, index=True)
    interests = Column(Text, nullable=False, default="[]")
    topics = Column(Text, nullable=False, default="[]")
    source = Column(String(200), nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending", index=True)
    confirmation_token = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Appointment(Base):
    """An appointment / call-booking request (public form, no login).

    ``status`` is one of: pending | confirmed | declined | completed.
    Dr. LeeAnn Roberts is the person to talk to for appointments.
    """

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, index=True)
    topic = Column(String(500), nullable=False, default="")
    preferred_date = Column(Date, nullable=True)
    preferred_time = Column(String(50), nullable=True)
    notes = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class OutreachEntry(Base):
    """One outreach activity log entry (logged going forward only)."""

    __tablename__ = "outreach_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    program = Column(String(200), nullable=False)
    channel = Column(String(200), nullable=False, default="")
    audience = Column(String(200), nullable=False, default="")
    contacts_reached = Column(Integer, nullable=False, default=0)
    subject = Column(String(500), nullable=False, default="")
    notes = Column(Text, nullable=False, default="")
