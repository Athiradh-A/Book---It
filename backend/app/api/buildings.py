from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.models import Building
from pydantic import BaseModel, ConfigDict

class BuildingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str

router = APIRouter(prefix="/buildings", tags=["Buildings"])

@router.get("/", response_model=List[BuildingSchema])
def get_buildings(db: Session = Depends(get_db)):
    return db.query(Building).all()
