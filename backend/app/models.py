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
    """DEPRECATED — replaced by AvailabilitySlot + Booking (slot-based
    booking with Dr. Roberts). Kept only so an existing database's table
    is not orphaned by the ORM; no endpoint uses it anymore."""

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


# ------------------------- Core: reach (audiences) -----------------------
# The platform's job is REACH: the Center reaching the students who need
# it. Audiences are groups of people to reach, built from student-org
# lists shared WITH the org's agreement, manual adds, org-rep submissions,
# or self-signup. Seed ZERO contacts — no roster exists.


class Audience(Base):
    """A group of people the Center wants to reach, tied to a source org
    (NSBE, URMC, CampusGroups, or a custom org name)."""

    __tablename__ = "audiences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source_org = Column(String(200), nullable=False, default="", index=True)
    description = Column(Text, nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Contact(Base):
    """One person the Center can reach.

    ``source`` is one of: upload | manual | org-submission | self-signup.
    ``interests`` / ``tags`` are stored as JSON arrays in text columns.
    Opted-out contacts are excluded from every campaign.
    """

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    audience_id = Column(Integer, ForeignKey("audiences.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False, default="")
    email = Column(String(320), nullable=False, index=True)
    source_org = Column(String(200), nullable=False, default="", index=True)
    interests = Column(Text, nullable=False, default="[]")
    tags = Column(Text, nullable=False, default="[]")
    source = Column(String(30), nullable=False, default="manual", index=True)
    opted_out = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class OrgSubmission(Base):
    """A student org's representative submitting their group's contacts.

    Submissions land as "pending review" — staff approve them into an
    audience (never auto-added). ``contacts_json`` holds the submitted
    rows: [{name, email, interests: [...]}].
    ``status`` is one of: pending | approved | rejected.
    """

    __tablename__ = "org_submissions"

    id = Column(Integer, primary_key=True, index=True)
    org_name = Column(String(200), nullable=False, index=True)
    rep_name = Column(String(200), nullable=False, default="")
    rep_email = Column(String(320), nullable=False, index=True)
    notes = Column(Text, nullable=False, default="")
    contacts_json = Column(Text, nullable=False, default="[]")
    status = Column(String(20), nullable=False, default="pending", index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


# ------------------------ Core: reach (campaigns) ------------------------


class Campaign(Base):
    """A newsletter issue sent to an audience segment.

    Campaigns ARE the newsletter: staff compose an issue (subject +
    message) and pick resources from the platform's real resource list
    to feature in it (``resource_ids``); sending goes to confirmed
    newsletter subscribers and/or the selected audiences.

    ``status`` is one of: draft | queued | sent | partially_sent.
    "queued" means ready to send but no SMTP is configured — the content
    and recipient list are visible, and nothing is claimed sent.
    ``audience_ids`` / ``org_filter`` / ``interest_filter`` define the
    segment; ``include_self_signup`` also pulls in confirmed opt-in
    newsletter subscribers.
    """

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    sender_name = Column(String(200), nullable=False, default="Center for Belonging")
    # JSON list of resource ids featured in this issue, in display order.
    resource_ids = Column(Text, nullable=False, default="[]")
    audience_ids = Column(Text, nullable=False, default="[]")
    org_filter = Column(String(200), nullable=False, default="")
    interest_filter = Column(String(200), nullable=False, default="")
    include_self_signup = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=False, default="")


class CampaignRecipient(Base):
    """One recipient of one campaign, with per-recipient send status.

    ``status`` is one of: queued | sent | failed.
    """

    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    name = Column(String(200), nullable=False, default="")
    source = Column(String(30), nullable=False, default="")
    status = Column(String(20), nullable=False, default="queued", index=True)
    error = Column(Text, nullable=False, default="")
    sent_at = Column(DateTime, nullable=True)


# ------------------- Core: real booking (slots + bookings) ---------------
# Slot-based booking with Dr. LeeAnn Roberts. Slots start EMPTY — staff
# add Dr. Roberts' availability; nothing is invented here.


class AvailabilitySlot(Base):
    """One bookable time with Dr. LeeAnn Roberts.

    ``type`` is one of: call | in-person. ``status`` is open | booked.
    Times are "HH:MM" 24-hour strings.
    """

    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    type = Column(String(20), nullable=False, default="call")
    host = Column(String(200), nullable=False, default="Dr. LeeAnn Roberts")
    status = Column(String(20), nullable=False, default="open", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Booking(Base):
    """A confirmed booking of one availability slot.

    ``status`` is one of: booked | cancelled. Cancelling re-opens the slot.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("availability_slots.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, index=True)
    purpose = Column(String(500), nullable=False, default="")
    status = Column(String(20), nullable=False, default="booked", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    cancelled_at = Column(DateTime, nullable=True)


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
