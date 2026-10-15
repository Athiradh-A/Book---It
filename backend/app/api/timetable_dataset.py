import csv
import io
from datetime import datetime, time
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.api.deps import require_role
from app.db.session import get_db
from app.models.models import Building, Room, Course, Faculty, User, Timetable, Booking, BookingHold, Maintenance, BookingStatus

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

SLOT_TIMES = [
    ("08:00", "08:50"), ("08:50", "09:40"), ("09:40", "10:30"),
    ("10:45", "11:35"), ("11:35", "12:25"), ("12:25", "13:15"),
    ("13:15", "14:05"), ("14:05", "14:55"), ("14:55", "15:45"),
    ("15:45", "16:35"), ("16:35", "17:25"),
]

def build_free_slot_rows(db: Session, date_value: str, building_code: str | None = None):
    try:
        day = datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(422, "date must use YYYY-MM-DD")
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
    query = db.query(Room).filter(Room.is_active.is_(True), Room.room_type == "CLASSROOM")
    if building_code:
        query = query.filter(Room.academic_block.ilike(building_code.upper().replace("-", "")))
    rooms = query.order_by(Room.academic_block, Room.code).all()
    rows = []
    now = datetime.utcnow()
    for room in rooms:
        classes = db.query(Timetable).filter(
            Timetable.room_id == room.id, Timetable.day_of_week == day.weekday(),
            Timetable.status == "ACTIVE", Timetable.effective_from <= day_end,
            Timetable.effective_to >= day_start
        ).all()
        bookings = db.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING_FACULTY_APPROVAL]),
            Booking.start_time < day_end, Booking.end_time > day_start
        ).all()
        holds = db.query(BookingHold).filter(
            BookingHold.room_id == room.id, BookingHold.status == "ACTIVE",
            BookingHold.expires_at > now, BookingHold.start_time < day_end,
            BookingHold.end_time > day_start
        ).all()
        maintenance = db.query(Maintenance).filter(
            Maintenance.room_id == room.id, Maintenance.status != "COMPLETED",
            Maintenance.start_datetime < day_end, Maintenance.end_datetime > day_start
        ).all()
        digits = room.code.split("-", 1)[-1] if "-" in room.code else ""
        for index, (start, end) in enumerate(SLOT_TIMES, start=1):
            slot_start = day.replace(hour=int(start[:2]), minute=int(start[3:]), second=0, microsecond=0)
            slot_end = day.replace(hour=int(end[:2]), minute=int(end[3:]), second=0, microsecond=0)
            class_busy = any(datetime.strptime(x.start_time, "%H:%M").time() < slot_end.time() and datetime.strptime(x.end_time, "%H:%M").time() > slot_start.time() for x in classes)
            booking_busy = any(x.start_time < slot_end and x.end_time > slot_start for x in bookings)
            hold_busy = any(x.start_time < slot_end and x.end_time > slot_start for x in holds)
            maintenance_busy = any(x.start_datetime < slot_end and x.end_datetime > slot_start for x in maintenance)
            status_value = "AVAILABLE"
            if class_busy: status_value = "TIMETABLE_OCCUPIED"
            elif booking_busy: status_value = "BOOKING_OCCUPIED"
            elif hold_busy: status_value = "HELD"
            elif maintenance_busy: status_value = "MAINTENANCE"
            rows.append({
                "classroom_id": room.code, "building": room.academic_block or (room.building.code if room.building else ""),
                "floor": int(digits[0]) if len(digits) == 3 and digits.isdigit() else None,
                "class_number": digits[-2:] if len(digits) == 3 and digits.isdigit() else None,
                "room_id": room.id, "date": date_value, "day_of_week": day.weekday(),
                "slot": index, "start_time": start, "end_time": end, "status": status_value,
                "is_free": status_value == "AVAILABLE"
            })
    return rows

@router.get("/free-slots")
def classroom_free_slots(date: str = Query(...), building: str | None = Query(default=None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"date": date, "building": building, "slots": build_free_slot_rows(db, date, building)}

@router.get("/free-slots.csv")
def export_classroom_free_slots(date: str = Query(...), building: str | None = Query(default=None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = build_free_slot_rows(db, date, building)
    columns = ["classroom_id", "building", "floor", "class_number", "room_id", "date", "day_of_week", "slot", "start_time", "end_time", "status", "is_free"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    filename = f"classroom_free_slots_{date}_{building or 'all'}.csv"
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
