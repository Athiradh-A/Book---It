from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class AmenityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    description: Optional[str] = None
    resource_kind: str = "EQUIPMENT"
    quantity: int = Field(default=1, ge=1)
    capacity: Optional[int] = Field(default=None, ge=1)
    location: Optional[str] = None
    requires_approval: bool = True
    status: str = "AVAILABLE"

class AmenityOut(AmenityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class AmenityBookingCreate(BaseModel):
    amenity_id: int
    start_time: datetime
    end_time: datetime
    quantity: int = Field(default=1, ge=1)
    purpose: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

class AmenityBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amenity_id: int
    requester_id: int
    start_time: datetime
    end_time: datetime
    quantity: int
    purpose: str
    status: str
    decision_comment: Optional[str] = None
    created_at: datetime

class AmenityDecision(BaseModel):
    decision: str
    comment: str = Field(min_length=1, max_length=1000)
