"""Pydantic schemas for API request/response validation.

Rules: validate carefully, never invent new business rules - mirrors the
existing tables and the old Tkinter dialogs."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

DateStr = str  # YYYY-MM-DD, validated below


def validate_date(value: str) -> str:
    from datetime import datetime

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError("date must be YYYY-MM-DD")
    return value


class SettingsIn(BaseModel):
    unit_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    toilet_daily_count: Optional[int] = Field(default=None, ge=0, le=99)
    guard_daily_count: Optional[int] = Field(default=None, ge=0, le=99)


class SquadIn(BaseModel):
    group_code: Literal["A", "B"]
    number: int = Field(ge=1, le=99)
    name: Optional[str] = None
    size: int = 0


class SquadPatch(BaseModel):
    name: Optional[str] = None
    size: Optional[int] = Field(default=None, ge=0, le=10000)
    number: Optional[int] = Field(default=None, ge=0, le=99)


class StudentIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    squad_id: Optional[int] = None
    father_name: Optional[str] = None
    national_id: Optional[str] = None
    birth_date: Optional[DateStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    rank: Optional[str] = None
    enlistment_date: Optional[DateStr] = None
    notes: Optional[str] = None

    @field_validator("birth_date", "enlistment_date")
    @classmethod
    def _dates(cls, v):
        if v:
            return validate_date(v)
        return v


class StudentPatch(StudentIn):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class GenerateWeekIn(BaseModel):
    start_date: DateStr
    toilet_count: Optional[int] = Field(default=None, ge=0, le=99)
    guard_count: Optional[int] = Field(default=None, ge=0, le=99)
    notes: Optional[str] = None

    @field_validator("start_date")
    @classmethod
    def _date(cls, v):
        return validate_date(v)


class AssignmentUpsertIn(BaseModel):
    """PUT semantics: full upsert of one cell (week, day, service).

    squad_id=None clears the assignment squad, matching db.upsert_assignment."""

    squad_id: Optional[int] = None
    count: int = Field(default=0, ge=0, le=999)
    notes: Optional[str] = None


class AssignmentPatchIn(BaseModel):
    """PATCH semantics: partial edit, squad_id omitted means "leave unchanged"
    - exactly the legacy db.update_assignment behaviour."""

    squad_id: Optional[int] = None
    set_squad_null: bool = False
    count: Optional[int] = Field(default=None, ge=0, le=999)
    notes: Optional[str] = None


class OptionalServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    week_id: Optional[int] = None
    date: Optional[DateStr] = None
    count: int = Field(default=0, ge=0, le=9999)
    receiver: Optional[str] = None
    squad_id: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def _date(cls, v):
        if v:
            return validate_date(v)
        return v


class OptionalServicePatch(OptionalServiceIn):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


ReportMode = Literal["path", "open", "print", "download"]


class WeeklyReportIn(BaseModel):
    week_id: int = Field(ge=1)
    service: Literal["guard", "restaurant", "kitchen", "cleaning", "toilet"]
    mode: ReportMode = "path"
