import csv
import io
import re
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import Building, Room

router = APIRouter(prefix="/resources", tags=["Room inventory"])
ROOM_CODE = re.compile(r"^[A-Z]-[1-9][0-9]{2}$")

@router.post("/rooms/import-inventory", dependencies=[Depends(require_role(["ADMIN"]))])
async def import_room_inventory(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a CSV file")
    raw = await file.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise HTTPException(413, "Room inventory CSV exceeds 4 MB")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded")
    required = {"classroom_id", "building", "capacity"}
    if not reader.fieldnames or not required.issubset({x.strip() for x in reader.fieldnames}):
        raise HTTPException(422, "Required columns: classroom_id, building, capacity. Optional: room_type, active")
    created, updated, errors = 0, 0, []
    for line, raw_row in enumerate(reader, start=2):
        row = {str(k).strip(): (v or "").strip() for k, v in raw_row.items() if k}
        try:
            code = row["classroom_id"].upper()
            building_code = row["building"].upper().replace("-", "")
            if not ROOM_CODE.fullmatch(code):
                raise ValueError("classroom_id must follow a pattern such as C-101 (letter, hyphen, three digits)")
            capacity = int(row["capacity"])
            if capacity < 1:
                raise ValueError("capacity must be a positive integer")
            building = db.query(Building).filter(Building.code.ilike(building_code)).first()
            if not building:
                building = Building(code=building_code, name=f"Academic Block {building_code[-1]}")
                db.add(building); db.flush()
            room = db.query(Room).filter(Room.code.ilike(code), Room.academic_block.ilike(building_code)).first()
            if room:
                room.capacity = capacity
                room.room_type = row.get("room_type") or "CLASSROOM"
                room.is_active = row.get("active", "true").lower() not in {"false", "0", "no", "inactive"}
                room.building_id = building.id
                updated += 1
            else:
                room = Room(code=code, building_id=building.id, academic_block=building_code, room_type=row.get("room_type") or "CLASSROOM", capacity=capacity, is_active=row.get("active", "true").lower() not in {"false", "0", "no", "inactive"})
                db.add(room); created += 1
        except Exception as exc:
            errors.append({"row": line, "classroom_id": row.get("classroom_id"), "error": str(exc)})
    if errors and created == 0 and updated == 0:
        db.rollback()
    else:
        db.commit()
    return {"created": created, "updated": updated, "errors": errors, "message": "Room inventory is ready for timetable imports."}
