from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class RegistrationEventCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: Optional[str] = None
    starts_at: datetime
    registration_deadline: Optional[datetime] = None
    capacity: int = Field(ge=1)
    room_id: Optional[int] = None

class RegistrationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    faculty_id: int
    room_id: Optional[int]
    name: str
    description: Optional[str]
    starts_at: datetime
    registration_deadline: Optional[datetime]
    capacity: int
    published: bool
    applicant_count: int = 0
    confirmed_count: int = 0
    room_code: Optional[str] = None

class TicketHoldCreate(BaseModel):
    roll_number: str = Field(min_length=3, max_length=40)
    participant_name: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=120)

class TicketConfirm(BaseModel):
    booking_id: str

class TicketApplicant(BaseModel):
    participant_name: str
    roll_number: str
    department: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
