from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.deps import require_role
from app.schemas.resources import BuildingCreate, BuildingOut, RoomCreate, RoomOut, EquipmentCreate, EquipmentOut, TimetableOut
from app.services.resource_service import ResourceService
from app.services.timetable_service import TimetableService
import shutil
import os

router = APIRouter(prefix="/resources", tags=["Resources"])

# --- Buildings ---
@router.post("/buildings", response_model=BuildingOut, dependencies=[Depends(require_role(["ADMIN"]))])
def create_building(building_in: BuildingCreate, db: Session = Depends(get_db)):
    return ResourceService.create_building(db, building_in)

@router.get("/buildings", response_model=List[BuildingOut])
def get_buildings(db: Session = Depends(get_db)):
    return ResourceService.get_buildings(db)

# --- Equipment ---
@router.post("/equipment", response_model=EquipmentOut, dependencies=[Depends(require_role(["ADMIN"]))])
def create_equipment(equipment_in: EquipmentCreate, db: Session = Depends(get_db)):
    return ResourceService.create_equipment(db, equipment_in)

@router.get("/equipment", response_model=List[EquipmentOut])
def get_equipment(db: Session = Depends(get_db)):
    return ResourceService.get_equipment(db)

# --- Rooms ---
@router.post("/rooms", response_model=RoomOut, dependencies=[Depends(require_role(["ADMIN"]))])
def create_room(room_in: RoomCreate, db: Session = Depends(get_db)):
    return ResourceService.create_room(db, room_in)

@router.get("/rooms", response_model=List[RoomOut])
def get_rooms(building_id: int = None, db: Session = Depends(get_db)):
    return ResourceService.get_rooms(db, building_id)

# --- Timetables ---
@router.post("/timetables/import", dependencies=[Depends(require_role(["ADMIN"]))])
async def import_timetable(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Save file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        count, errors = TimetableService.import_from_file(db, temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return {"imported": count, "errors": errors}

@router.get("/timetables", response_model=List[TimetableOut])
def get_timetables(db: Session = Depends(get_db)):
    return TimetableService.get_all_timetables(db)

