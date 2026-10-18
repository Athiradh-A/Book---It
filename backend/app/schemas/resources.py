from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Buildings ---
class BuildingBase(BaseModel):
    name: str
    code: str


class BuildingCreate(BuildingBase):
    pass


class BuildingOut(BuildingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Equipment ---
class EquipmentBase(BaseModel):
    name: str


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentOut(EquipmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- Rooms ---
class RoomBase(BaseModel):
    code: str
    building_id: Optional[int] = None
    academic_block: Optional[str] = None
    room_type: str
    capacity: int = Field(..., ge=1)
    is_active: bool = True


class RoomCreate(RoomBase):
    equipment_ids: List[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_classroom_capacity(self):
        if (
            self.room_type.strip().upper() == "CLASSROOM"
            and not 40 <= self.capacity <= 80
        ):
            raise ValueError(
                "Classroom capacity must be between 40 and 80 students."
            )
        return self


class RoomOut(RoomBase):
    id: int
    building: Optional[BuildingOut] = None
    model_config = ConfigDict(from_attributes=True)


# --- Timetables ---
class TimetableBase(BaseModel):
    course_id: Optional[int] = None
    faculty_id: Optional[int] = None
    room_id: int
    day_of_week: int = Field(
        ...,
        ge=0,
        le=6,
        description="Monday=0; Sunday=6",
    )
    start_time: str
    end_time: str
    semester: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "ACTIVE"


class TimetableCreate(TimetableBase):
    pass


class TimetableOut(TimetableBase):
    id: int
    model_config = ConfigDict(from_attributes=True)