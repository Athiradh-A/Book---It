from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.models import BookingStatus

class EventRequestCreate(BaseModel):
    room_id: int
    event_name: str
    event_category: str
    description: str
    date: datetime
    start_time: datetime
    end_time: datetime
    expected_attendees: int

class EventRequestOut(BaseModel):
    id: int
    room_id: int
    event_name: str
    status: BookingStatus
    current_approval_level: int
    requested_by: int
    
    class Config:
        from_attributes = True

class ApprovalDecision(BaseModel):
    decision: str # APPROVED, REJECTED, RETURNED
    comment: str = Field(..., min_length=1)

class NotificationOut(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
