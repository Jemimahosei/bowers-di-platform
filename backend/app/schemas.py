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


class AppointmentCreate(BaseModel):
    name: str
    email: str
    topic: str = ""
    preferred_date: _date | None = None
    preferred_time: str | None = None
    notes: str = ""


class AppointmentOut(BaseModel):
    id: int
    name: str
    email: str
    topic: str
    preferred_date: _date | None = None
    preferred_time: str | None = None
    notes: str
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in {"pending", "confirmed", "declined", "completed"}:
            raise ValueError(
                "status must be pending, confirmed, declined, or completed"
            )
        return v


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
