"""Pydantic schemas for request/response bodies."""

from __future__ import annotations

import json
from datetime import date as _date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


# --------------------------------- Users ---------------------------------


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    # Registration ALWAYS creates role "student". Supplying admin/faculty
    # here is rejected (400); an admin promotes roles afterwards.
    role: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        if v not in {"student", "faculty", "admin"}:
            raise ValueError("role must be student, faculty, or admin")
        return v


# ------------------------------- Resources -------------------------------


class ResourceBase(BaseModel):
    title: str
    description: str
    category: str
    audience: str
    link: str = ""


class ResourceCreate(ResourceBase):
    pass


class ResourceOut(ResourceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ------------------------------ Conferences ------------------------------


class ConferenceBase(BaseModel):
    name: str
    date: _date | None = None
    end_date: _date | None = None
    location: str = ""
    status: str = "upcoming"
    description: str = ""
    link: str = ""
    attendees: int | None = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in {"upcoming", "past", "cancelled", "tba"}:
            raise ValueError("status must be upcoming, past, cancelled, or tba")
        return v


class ConferenceCreate(ConferenceBase):
    pass


class ConferenceOut(ConferenceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ParticipationCreate(BaseModel):
    # Optional: an admin may record participation for another user.
    # A non-admin recording their own attendance omits this.
    user_id: int | None = None
    note: str = ""


class ParticipationOut(BaseModel):
    id: int
    conference_id: int
    user_id: int | None
    note: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --------------------------------- Events ---------------------------------


class EventBase(BaseModel):
    name: str
    description: str = ""
    date: _date | None = None
    status: str = "active"
    category: str = "program"
    location: str | None = None

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in {"program", "conference", "workshop", "community"}:
            raise ValueError(
                "category must be program, conference, workshop, or community"
            )
        return v


class EventCreate(EventBase):
    pass


class EventOut(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ------------------------------ Newsletter -------------------------------


class NewsletterSignup(BaseModel):
    name: str = ""
    email: str
    interests: list[str] = []
    topics: list[str] = []
    source: str = ""


class NewsletterSubscriberOut(BaseModel):
    id: int
    name: str
    email: str
    interests: list[str] = []
    topics: list[str] = []
    source: str
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("interests", "topics", mode="before")
    @classmethod
    def _parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return v or []


class NewsletterUnsubscribe(BaseModel):
    email: str


# ----------------------------- Appointments ------------------------------
# Slot-based booking with Dr. LeeAnn Roberts (replaces the old request
# form). Slots start empty; staff add availability.


class SlotCreate(BaseModel):
    date: _date
    start_time: str
    end_time: str
    type: str = "call"
    host: str = "Dr. LeeAnn Roberts"

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in {"call", "in-person"}:
            raise ValueError("type must be call or in-person")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def _valid_time(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError("time must be HH:MM")
        hh, mm = int(parts[0]), int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError("time must be a valid 24-hour HH:MM")
        return f"{hh:02d}:{mm:02d}"


class SlotOut(BaseModel):
    id: int
    date: _date
    start_time: str
    end_time: str
    type: str
    host: str
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    name: str
    email: str
    purpose: str = ""


class BookingOut(BaseModel):
    id: int
    slot_id: int
    name: str
    email: str
    purpose: str
    status: str
    created_at: datetime | None = None
    cancelled_at: datetime | None = None
    slot: SlotOut | None = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------- Audiences & contacts --------------------------


class AudienceCreate(BaseModel):
    name: str
    source_org: str = ""
    description: str = ""


class AudienceOut(BaseModel):
    id: int
    name: str
    source_org: str
    description: str
    created_at: datetime | None = None
    contact_count: int = 0
    opted_out_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(BaseModel):
    name: str = ""
    email: str
    source_org: str = ""
    interests: list[str] = []
    tags: list[str] = []


class ContactOut(BaseModel):
    id: int
    audience_id: int
    name: str
    email: str
    source_org: str
    interests: list[str] = []
    tags: list[str] = []
    source: str
    opted_out: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("interests", "tags", mode="before")
    @classmethod
    def _parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return v or []

    @field_validator("opted_out", mode="before")
    @classmethod
    def _to_bool(cls, v):
        return bool(v)


class ContactUpdate(BaseModel):
    name: str | None = None
    interests: list[str] | None = None
    tags: list[str] | None = None
    opted_out: bool | None = None


class ContactIn(BaseModel):
    """One contact row inside an org submission."""

    name: str = ""
    email: str
    interests: list[str] = []


class OrgSubmissionCreate(BaseModel):
    org_name: str
    rep_name: str = ""
    rep_email: str
    notes: str = ""
    contacts: list[ContactIn] = []


class OrgSubmissionOut(BaseModel):
    id: int
    org_name: str
    rep_name: str
    rep_email: str
    notes: str
    contacts: list[ContactIn] = []
    status: str
    created_at: datetime | None = None
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("contacts", mode="before")
    @classmethod
    def _parse_contacts(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return v or []


class OrgSubmissionReview(BaseModel):
    decision: str
    # Optional: add approved contacts to this existing audience; otherwise
    # a new audience is created from the org name.
    audience_id: int | None = None

    @field_validator("decision")
    @classmethod
    def _valid_decision(cls, v: str) -> str:
        if v not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        return v


# ------------------------------ Campaigns --------------------------------


class CampaignCreate(BaseModel):
    subject: str
    body: str
    sender_name: str = "Center for Belonging"
    # Resources from the platform's real resource list to feature in
    # this newsletter issue (ids, in display order).
    resource_ids: list[int] = []
    audience_ids: list[int] = []
    org_filter: str = ""
    interest_filter: str = ""
    include_self_signup: bool = False


class CampaignUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    sender_name: str | None = None
    resource_ids: list[int] | None = None
    audience_ids: list[int] | None = None
    org_filter: str | None = None
    interest_filter: str | None = None
    include_self_signup: bool | None = None


class CampaignRecipientOut(BaseModel):
    id: int
    campaign_id: int
    email: str
    name: str
    source: str
    status: str
    error: str = ""
    sent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignOut(BaseModel):
    id: int
    subject: str
    body: str
    sender_name: str
    resource_ids: list[int] = []
    featured_resources: list[ResourceOut] = []
    audience_ids: list[int] = []
    org_filter: str
    interest_filter: str
    include_self_signup: bool = False
    status: str
    created_at: datetime | None = None
    sent_at: datetime | None = None
    error: str = ""
    recipient_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("resource_ids", "audience_ids", mode="before")
    @classmethod
    def _parse_ids(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            if not isinstance(parsed, list):
                return []
            return [int(x) for x in parsed]
        return v or []

    @field_validator("include_self_signup", mode="before")
    @classmethod
    def _to_bool(cls, v):
        return bool(v)


# ------------------------------- Outreach --------------------------------


class OutreachBase(BaseModel):
    date: _date
    program: str
    channel: str = ""
    audience: str = ""
    contacts_reached: int = 0
    subject: str = ""
    notes: str = ""


class OutreachCreate(OutreachBase):
    pass


class OutreachOut(OutreachBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OutreachStats(BaseModel):
    total_entries: int
    total_contacts: int
    by_program: list[dict]


# ------------------------------ Dashboard --------------------------------


class DashboardOut(BaseModel):
    totals: dict
    participation_by_conference: list[dict]
    outreach_by_month: list[dict]
    subscribers_by_month: list[dict]
    appointments_by_status: dict
