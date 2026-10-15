import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import Building, Room, Course, Faculty, User, Timetable

router = APIRouter(prefix="/resources/timetables", tags=["Timetable dataset"])
DAY_MAP = {"MON": 0, "MONDAY": 0, "TUE": 1, "TUESDAY": 1, "WED": 2, "WEDNESDAY": 2, "THU": 3, "THURSDAY": 3, "FRI": 4, "FRIDAY": 4, "SAT": 5, "SATURDAY": 5, "SUN": 6, "SUNDAY": 6}

@router.post("/import-dataset", dependencies=[Depends(require_role(["ADMIN"]))])
async def import_classroom_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Upload a CSV file")
    raw = await file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, "Timetable CSV exceeds 8 MB")
    try:
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded")
    required = {"classroom_id", "building", "day_of_week", "start_time", "end_time", "semester"}
    if not rows.fieldnames or not required.issubset({x.strip() for x in rows.fieldnames}):
        raise HTTPException(422, "Required columns: classroom_id, building, day_of_week, start_time, end_time, semester. Optional: course_code, course_name, faculty_email, effective_from, effective_to")
    imported, errors = 0, []
    for line, raw_row in enumerate(rows, start=2):
        row = {str(k).strip(): (v or "").strip() for k, v in raw_row.items() if k}
        try:
            code, building_code = row["classroom_id"].upper(), row["building"].upper()
            building = db.query(Building).filter(Building.code.ilike(building_code)).first()
            candidates = db.query(Room).filter(Room.code.ilike(code)).all()
            room = next((candidate for candidate in candidates if
                (candidate.academic_block or "").replace("-", "").upper() == building_code or
                (building is not None and candidate.building_id == building.id)), None)
            if not room:
                raise ValueError(f"Classroom {code} was not found in building {building_code}; create the room inventory first")
            day_raw = row["day_of_week"].strip().upper()
            day = DAY_MAP.get(day_raw, int(day_raw) if day_raw.isdigit() else -1)
            if day < 0 or day > 6:
                raise ValueError("day_of_week must be 0-6 or a weekday name")
            start = datetime.strptime(row["start_time"], "%H:%M").strftime("%H:%M")
            end = datetime.strptime(row["end_time"], "%H:%M").strftime("%H:%M")
            if start >= end:
                raise ValueError("end_time must be later than start_time")
            effective_from = datetime.strptime(row["effective_from"], "%Y-%m-%d") if row.get("effective_from") else datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            effective_to = datetime.strptime(row["effective_to"], "%Y-%m-%d").replace(hour=23, minute=59, second=59) if row.get("effective_to") else datetime(2099, 12, 31, 23, 59, 59)
            if effective_to < effective_from:
                raise ValueError("effective_to must not precede effective_from")
            course_id = None
            if row.get("course_code"):
                course = db.query(Course).filter(Course.code == row["course_code"].upper()).first()
                if not course:
                    course = Course(code=row["course_code"].upper(), name=row.get("course_name") or row["course_code"].upper())
                    db.add(course); db.flush()
                course_id = course.id
            faculty_id = None
            if row.get("faculty_email"):
                user = db.query(User).filter(User.email.ilike(row["faculty_email"])).first()
                faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first() if user else None
                if not faculty:
                    raise ValueError(f"Faculty email {row['faculty_email']} is not linked to a faculty record")
                faculty_id = faculty.id
            duplicate = db.query(Timetable).filter(Timetable.room_id == room.id, Timetable.day_of_week == day, Timetable.start_time == start, Timetable.end_time == end, Timetable.semester == row["semester"], Timetable.effective_from == effective_from, Timetable.status == "ACTIVE").first()
            if duplicate:
                continue
            db.add(Timetable(course_id=course_id, faculty_id=faculty_id, room_id=room.id, day_of_week=day, start_time=start, end_time=end, semester=row["semester"], effective_from=effective_from, effective_to=effective_to, status="ACTIVE"))
            imported += 1
        except Exception as exc:
            errors.append({"row": line, "classroom_id": row.get("classroom_id"), "error": str(exc)})
    if errors and imported == 0:
        db.rollback()
    else:
        db.commit()
    return {"imported": imported, "errors": errors, "message": "Timetable entries imported. Free periods are derived from the absence of timetable, booking, hold, and maintenance conflicts."}
