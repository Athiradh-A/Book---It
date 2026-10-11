from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    id: str
    username: str
    full_name: str
    email: str
    role: str
    department: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UserRead(UserBase):
    pass

class EventRequestCreate(BaseModel):
    title: str
    purpose: str
    venue: str
    event_date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    expected_attendance: int
    budget: float = 0.0
    student_coordinator_id: str
    faculty_coordinator_id: str
    supporting_docs: Optional[str] = None

class ApprovalActionRequest(BaseModel):
    actor_id: str
    action: Optional[str] = "REQUEST_MEETING"  # APPROVE, REJECT, REQUEST_MEETING, RETURN_FOR_CLARIFICATION
    comments: Optional[str] = None

class EventRequestRead(BaseModel):
    id: int
    title: str
    purpose: str
    venue: str
    event_date: str
    start_time: str
    end_time: str
    expected_attendance: int
    budget: float
    student_coordinator_id: str
    faculty_coordinator_id: str
    supporting_docs: Optional[str] = None
    status: str
    current_stage: str
    created_at: datetime
    updated_at: datetime
    student_coordinator: Optional[UserRead] = None
    faculty_coordinator: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)

class ApprovalLogRead(BaseModel):
    id: int
    event_request_id: int
    actor_id: str
    actor_name: str
    actor_role: str
    stage: str
    action: str
    comments: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationRead(BaseModel):
    id: int
    user_id: str
    title: str
    message: str
    notification_type: str
    related_event_id: Optional[int] = None
    is_read: bool
    email_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
