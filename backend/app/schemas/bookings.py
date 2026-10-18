from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class AvailabilityRequest(BaseModel):
    date: datetime
    start_time: datetime
    end_time: datetime
    required_capacity: int
    required_equipment_ids: List[int] = []
    room_type: Optional[str] = None
    academic_block: Optional[str] = None
    building_id: Optional[int] = None

class ConflictInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    room_id: int
    code: str
    is_available: bool
    conflict_type: Optional[str] = None 
    details: Optional[str] = None

class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    room_id: int
    code: str
    is_available: bool
    conflict_type: Optional[str] = None
    details: Optional[str] = None

class HoldRequest(BaseModel):
    room_id: int
    start_time: str
    end_time: str
    expected_attendees: int = 1
    target_faculty_id: int

class HoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    hold_id: int # We will map this in the backend
    expires_at: datetime
    room_id: int

class ConfirmRequest(BaseModel):
    hold_id: int
    purpose: str
    expected_attendees: int
    assigned_faculty_email: str
