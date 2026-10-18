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
VALID_BLOCKS = {"AB1", "AB2", "AB3", "AB4"}


@router.post(
    "/rooms/import-inventory",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
async def import_room_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=415,
            detail="Upload a CSV file.",
        )

    raw = await file.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Room inventory CSV exceeds 4 MB.",
        )

    try:
        reader = csv.DictReader(
            io.StringIO(raw.decode("utf-8-sig"))
        )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded.",
        ) from exc

    required = {"classroom_id", "building", "capacity"}
    headers = {
        header.strip()
        for header in (reader.fieldnames or [])
    }

    if not reader.fieldnames or not required.issubset(headers):
        raise HTTPException(
            status_code=422,
            detail=(
                "Required columns: classroom_id, building, capacity. "
                "Optional: room_type, active."
            ),
        )

    created = 0
    updated = 0
    errors = []

    try:
        for line, raw_row in enumerate(reader, start=2):
            row = {
                str(key).strip(): (value or "").strip()
                for key, value in raw_row.items()
                if key
            }

            try:
                code = row["classroom_id"].upper()
                block = row["building"].upper().replace("-", "")
                room_type = (
                    row.get("room_type") or "CLASSROOM"
                ).strip().upper()
                active = row.get(
                    "active", "true"
                ).lower() not in {
                    "false", "0", "no", "inactive"
                }
                capacity = int(row["capacity"])

                if block not in VALID_BLOCKS:
                    raise ValueError(
                        "building must be AB1, AB2, AB3, or AB4"
                    )

                if not ROOM_CODE.fullmatch(code):
                    raise ValueError(
                        "classroom_id must follow a pattern such as C-101"
                    )

                if capacity < 1:
                    raise ValueError(
                        "capacity must be a positive integer"
                    )

                if room_type == "CLASSROOM" and not 40 <= capacity <= 80:
                    raise ValueError(
                        "classroom capacity must be between 40 and 80"
                    )

                building = (
                    db.query(Building)
                    .filter(Building.code.ilike(block))
                    .first()
                )

                if building is None:
                    building = Building(
                        code=block,
                        name=f"Academic Block {block[-1]}",
                    )
                    db.add(building)
                    db.flush()

                candidates = (
                    db.query(Room)
                    .filter(Room.code.ilike(code))
                    .all()
                )

                room = next(
                    (
                        candidate
                        for candidate in candidates
                        if (
                            (candidate.academic_block or "")
                            .replace("-", "")
                            .upper()
                            == block
                            or candidate.building_id == building.id
                        )
                    ),
                    None,
                )

                if room:
                    room.capacity = capacity
                    room.room_type = room_type
                    room.is_active = active
                    room.building_id = building.id
                    room.academic_block = block
                    updated += 1
                else:
                    db.add(
                        Room(
                            code=code,
                            building_id=building.id,
                            academic_block=block,
                            room_type=room_type,
                            capacity=capacity,
                            is_active=active,
                        )
                    )
                    created += 1

            except Exception as exc:
                errors.append({
                    "row": line,
                    "classroom_id": row.get("classroom_id"),
                    "error": str(exc),
                })

        if errors and created == 0 and updated == 0:
            db.rollback()
        else:
            db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": "Room inventory is ready for timetable imports.",
    }