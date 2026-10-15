from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.models import BookingStatus

class EventRequestCreate(BaseModel):
    room_id: int
    event_name: str = Field(..., min_length=3, max_length=200)
    event_category: str = "GENERAL"
    description: str = Field(..., min_length=10)
    date: datetime
    start_time: datetime
    end_time: datetime
    expected_attendees: int = Field(..., ge=1)
    department: Optional[str] = None
    responsible_faculty: Optional[str] = None
    discipline_faculty: Optional[str] = None
    infrastructure_needs: Optional[str] = None
    catering_needs: Optional[str] = None
    vehicle_needs: Optional[str] = None
    accommodation_needs: Optional[str] = None
    funding_source: Optional[str] = None
    funding_amount: Optional[float] = Field(default=None, ge=0)
    risk_assessment: Optional[str] = None

class EventRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    event_name: str
    status: BookingStatus
    current_approval_level: int
    requested_by: int
    date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    expected_attendees: Optional[int] = None

class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|RETURNED|MEETING_REQUESTED)$")
    comment: str = Field(..., min_length=1)
    preferred_meeting_at: Optional[datetime] = None

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    message: str
    is_read: bool
    created_at: datetime
