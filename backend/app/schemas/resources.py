from pydantic import BaseModel, Field
from typing import List, Optional

# --- Building Schemas ---
class BuildingBase(BaseModel):
    name: str
    code: str

class BuildingCreate(BuildingBase):
    pass

class BuildingOut(BuildingBase):
    id: int
    class Config:
        from_attributes = True

# --- Equipment Schemas ---
class EquipmentBase(BaseModel):
    name: str

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentOut(EquipmentBase):
    id: int
    class Config:
        from_attributes = True

# --- Room Schemas ---
class RoomBase(BaseModel):
    code: str
    building_id: Optional[int] = None
    academic_block: Optional[str] = None
    room_type: str
    capacity: int = Field(..., ge=1)
    is_active: bool = True

class RoomCreate(RoomBase):
    equipment_ids: List[int] = []

class RoomOut(RoomBase):
    id: int
    building: Optional[BuildingOut] = None
    class Config:
        from_attributes = True

# --- Timetable Schemas ---
class TimetableBase(BaseModel):
    course_id: int
    faculty_id: int
    room_id: int
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str # HH:MM
    end_time: str   # HH:MM
    semester: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "ACTIVE"

class TimetableCreate(TimetableBase):
    pass

class TimetableOut(TimetableBase):
    id: int
    class Config:
        from_attributes = True
