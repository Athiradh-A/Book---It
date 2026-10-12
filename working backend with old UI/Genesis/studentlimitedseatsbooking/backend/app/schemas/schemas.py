from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class StudentProfileBase(BaseModel):
    id: str # e.g. CB.EN.U4CSE22001
    user_id: str
    full_name: str
    email: str
    programme: str
    department: str
    current_academic_year: int
    graduating_batch: int
    verification_status: str = "VERIFIED"

    model_config = ConfigDict(from_attributes=True)

class StudentProfileRead(StudentProfileBase):
    pass

class EligibilityRuleCreate(BaseModel):
    is_open_to_all: bool = True
    allowed_programmes: List[str] = Field(default_factory=list)
    allowed_departments: List[str] = Field(default_factory=list)
    allowed_academic_years: List[int] = Field(default_factory=list)
    allowed_batches: List[int] = Field(default_factory=list)

class EligibilityRuleRead(BaseModel):
    id: int
    event_id: int
    is_open_to_all: bool
    allowed_programmes: List[str]
    allowed_departments: List[str]
    allowed_academic_years: List[int]
    allowed_batches: List[int]

    model_config = ConfigDict(from_attributes=True)

class EligibilityCheckResult(BaseModel):
    is_eligible: bool
    reason: str
    missing_profile: bool = False

class EventCreate(BaseModel):
    title: str
    description: str
    organizing_department: str
    event_category: str = "Workshop"
    start_datetime: datetime
    end_datetime: datetime
    venue: str
    faculty_contact: Optional[str] = None
    poster_url: Optional[str] = None
    publication_status: str = "PUBLISHED" # DRAFT, PUBLISHED, UNPUBLISHED, CANCELLED, COMPLETED
    is_registration_required: bool = True
    capacity_type: str = "LIMITED" # LIMITED, UNLIMITED, NONE_INFORMATIONAL
    total_capacity: Optional[int] = None
    registration_open_datetime: Optional[datetime] = None
    registration_close_datetime: Optional[datetime] = None
    allow_cancellation: bool = True
    cancellation_deadline: Optional[datetime] = None
    eligibility_rule: Optional[EligibilityRuleCreate] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    organizing_department: Optional[str] = None
    event_category: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    venue: Optional[str] = None
    faculty_contact: Optional[str] = None
    poster_url: Optional[str] = None
    publication_status: Optional[str] = None
    is_registration_required: Optional[bool] = None
    capacity_type: Optional[str] = None
    total_capacity: Optional[int] = None
    registration_open_datetime: Optional[datetime] = None
    registration_close_datetime: Optional[datetime] = None
    allow_cancellation: Optional[bool] = None
    cancellation_deadline: Optional[datetime] = None
    eligibility_rule: Optional[EligibilityRuleCreate] = None

class EventRead(BaseModel):
    id: int
    title: str
    description: str
    organizing_department: str
    event_category: str
    start_datetime: datetime
    end_datetime: datetime
    venue: str
    faculty_contact: Optional[str] = None
    poster_url: Optional[str] = None
    publication_status: str
    is_registration_required: bool
    capacity_type: str
    total_capacity: Optional[int] = None
    remaining_seats: Optional[int] = None
    registration_open_datetime: Optional[datetime] = None
    registration_close_datetime: Optional[datetime] = None
    allow_cancellation: bool
    cancellation_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    eligibility_rule: Optional[EligibilityRuleRead] = None
    current_status: Optional[str] = None # Calculated: Registration Open, Registration Full, etc.

    model_config = ConfigDict(from_attributes=True)

class EventRegistrationCreate(BaseModel):
    event_id: int
    student_profile_id: str

class EventRegistrationRead(BaseModel):
    id: int
    event_id: int
    student_profile_id: str
    registration_reference: str
    registration_status: str
    registration_timestamp: datetime
    cancellation_timestamp: Optional[datetime] = None
    event: Optional[EventRead] = None
    student_profile: Optional[StudentProfileRead] = None

    model_config = ConfigDict(from_attributes=True)

class AcademicCalendarEntryRead(BaseModel):
    id: int
    source_event_id: int
    title: str
    start_datetime: datetime
    end_datetime: datetime
    venue: str
    organizing_department: str
    description: str
    event_category: str
    calendar_status: str
    last_synced_at: datetime

    model_config = ConfigDict(from_attributes=True)
