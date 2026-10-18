import csv
import io
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.models import (
    Booking,
    BookingHold,
    BookingStatus,
    Building,
    Course,
    Faculty,
    Maintenance,
    Room,
    Timetable,
    User,
)

router = APIRouter(
    prefix="/resources/timetables",
    tags=["Timetable dataset"],
)

# Python weekday numbering:
# Monday=0, Tuesday=1, Wednesday=2, Thursday=3,
# Friday=4, Saturday=5, Sunday=6.
DAY_MAP = {
    "MON": 0,
    "MONDAY": 0,
    "TUE": 1,
    "TUESDAY": 1,
    "WED": 2,
    "WEDNESDAY": 2,
    "THU": 3,
    "THURSDAY": 3,
    "FRI": 4,
    "FRIDAY": 4,
    "SAT": 5,
    "SATURDAY": 5,
    "SUN": 6,
    "SUNDAY": 6,
}

VALID_BLOCKS = {"AB1", "AB2", "AB3", "AB4"}

SLOT_TIMES = [
    ("08:00", "08:50"),
    ("08:50", "09:40"),
    ("09:40", "10:30"),
    ("10:45", "11:35"),
    ("11:35", "12:25"),
    ("12:25", "13:15"),
    ("13:15", "14:05"),
    ("14:05", "14:55"),
    ("14:55", "15:45"),
    ("15:45", "16:35"),
    ("16:35", "17:25"),
]


def normalize_weekday(value: str) -> int:
    """Convert a weekday name or number to Python's 0-6 format."""
    text = (value or "").strip().upper()

    if text in DAY_MAP:
        return DAY_MAP[text]

    if text.isdigit() and 0 <= int(text) <= 6:
        return int(text)

    raise ValueError(
        "day_of_week must be 0-6 or a weekday name such as MON"
    )


def _read_date(value: str, field_name: str) -> datetime:
    """Parse a YYYY-MM-DD value into a datetime."""
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD"
        ) from exc


@router.post(
    "/import-dataset",
    dependencies=[Depends(require_role(["ADMIN"]))],
)
async def import_classroom_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Import classroom_timetable_template.csv.

    Required columns:
    classroom_id, building, day_of_week, start_time, end_time, semester

    Optional columns:
    course_code, course_name, faculty_email,
    effective_from, effective_to
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=415,
            detail="Upload a CSV file.",
        )

    raw = await file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Timetable CSV exceeds 8 MB.",
        )

    try:
        csv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded.",
        ) from exc

    reader = csv.DictReader(io.StringIO(csv_text))

    required = {
        "classroom_id",
        "building",
        "day_of_week",
        "start_time",
        "end_time",
        "semester",
    }

    headers = {
        str(header).strip()
        for header in (reader.fieldnames or [])
    }

    if not reader.fieldnames or not required.issubset(headers):
        raise HTTPException(
            status_code=422,
            detail=(
                "Required columns: classroom_id, building, day_of_week, "
                "start_time, end_time, semester. Optional: course_code, "
                "course_name, faculty_email, effective_from, effective_to."
            ),
        )

    imported = 0
    skipped = 0
    errors = []

    try:
        for line, raw_row in enumerate(reader, start=2):
            row = {
                str(key).strip(): (value or "").strip()
                for key, value in raw_row.items()
                if key
            }

            try:
                room_code = row["classroom_id"].upper()
                block = row["building"].upper().replace("-", "")

                if block not in VALID_BLOCKS:
                    raise ValueError(
                        "building must be AB1, AB2, AB3, or AB4"
                    )

                building = (
                    db.query(Building)
                    .filter(Building.code.ilike(block))
                    .first()
                )

                possible_rooms = (
                    db.query(Room)
                    .filter(Room.code.ilike(room_code))
                    .all()
                )

                room = next(
                    (
                        candidate
                        for candidate in possible_rooms
                        if (
                            (candidate.academic_block or "")
                            .replace("-", "")
                            .upper()
                            == block
                            or (
                                building is not None
                                and candidate.building_id == building.id
                            )
                        )
                    ),
                    None,
                )

                if room is None:
                    raise ValueError(
                        f"Classroom {room_code} was not found in {block}; "
                        "import the room inventory first."
                    )

                if (
                    (room.room_type or "").strip().upper() == "CLASSROOM"
                    and not 40 <= room.capacity <= 80
                ):
                    raise ValueError(
                        "Classroom capacity must be 40-80; "
                        f"room currently has capacity {room.capacity}."
                    )

                # Convert MON/TUE/... to Monday=0 through Sunday=6.
                weekday = normalize_weekday(row["day_of_week"])

                start = datetime.strptime(
                    row["start_time"], "%H:%M"
                ).strftime("%H:%M")

                end = datetime.strptime(
                    row["end_time"], "%H:%M"
                ).strftime("%H:%M")

                if start >= end:
                    raise ValueError(
                        "end_time must be later than start_time"
                    )

                if not row.get("semester"):
                    raise ValueError("semester cannot be blank")

                effective_from = (
                    _read_date(
                        row["effective_from"],
                        "effective_from",
                    )
                    if row.get("effective_from")
                    else datetime.utcnow().replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                )

                effective_to = (
                    _read_date(
                        row["effective_to"],
                        "effective_to",
                    ).replace(
                        hour=23,
                        minute=59,
                        second=59,
                        microsecond=999999,
                    )
                    if row.get("effective_to")
                    else datetime(
                        2099, 12, 31, 23, 59, 59, 999999
                    )
                )

                if effective_to < effective_from:
                    raise ValueError(
                        "effective_to must not precede effective_from"
                    )

                # Find or create the course when course_code is supplied.
                course_id = None
                course_code = row.get("course_code", "").upper()

                if course_code:
                    course = (
                        db.query(Course)
                        .filter(Course.code == course_code)
                        .first()
                    )

                    if course is None:
                        course = Course(
                            code=course_code,
                            name=row.get("course_name") or course_code,
                        )
                        db.add(course)
                        db.flush()
                    elif (
                        row.get("course_name")
                        and course.name == course.code
                    ):
                        course.name = row["course_name"]

                    course_id = course.id

                # Faculty is optional. If an email is supplied, it must
                # be connected to an existing faculty record.
                faculty_id = None
                faculty_email = row.get("faculty_email", "").strip()

                if faculty_email:
                    user = (
                        db.query(User)
                        .filter(User.email.ilike(faculty_email))
                        .first()
                    )

                    faculty = (
                        db.query(Faculty)
                        .filter(Faculty.user_id == user.id)
                        .first()
                        if user
                        else None
                    )

                    if faculty is None:
                        raise ValueError(
                            f"Faculty email {faculty_email} is not "
                            "linked to a faculty record"
                        )

                    faculty_id = faculty.id

                # Skip duplicate timetable entries.
                duplicate = (
                    db.query(Timetable)
                    .filter(
                        Timetable.room_id == room.id,
                        Timetable.day_of_week == weekday,
                        Timetable.start_time == start,
                        Timetable.end_time == end,
                        Timetable.semester == row["semester"],
                        Timetable.effective_from == effective_from,
                        Timetable.status == "ACTIVE",
                    )
                    .first()
                )

                if duplicate:
                    skipped += 1
                    continue

                db.add(
                    Timetable(
                        course_id=course_id,
                        faculty_id=faculty_id,
                        room_id=room.id,
                        day_of_week=weekday,
                        start_time=start,
                        end_time=end,
                        semester=row["semester"],
                        effective_from=effective_from,
                        effective_to=effective_to,
                        status="ACTIVE",
                    )
                )
                imported += 1

            except Exception as exc:
                errors.append({
                    "row": line,
                    "classroom_id": row.get("classroom_id"),
                    "error": str(exc),
                })

        if errors and imported == 0:
            db.rollback()
        else:
            db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "imported": imported,
        "skipped_duplicates": skipped,
        "errors": errors,
        "message": (
            "Timetable import finished. Availability uses the selected "
            "calendar date's weekday."
        ),
    }


def build_free_slot_rows(
    db: Session,
    date_value: str,
    building_code: str | None = None,
):
    """Return timetable and booking status for each classroom time slot."""
    try:
        selected_date = _read_date(date_value, "date")
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    day_start = selected_date.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_end = (
        day_start
        + timedelta(days=1)
        - timedelta(microseconds=1)
    )

    query = db.query(Room).filter(
        Room.is_active.is_(True),
        Room.room_type.ilike("CLASSROOM"),
        Room.capacity >= 40,
        Room.capacity <= 80,
    )

    if building_code:
        normalized_block = building_code.upper().replace("-", "")

        if normalized_block not in VALID_BLOCKS:
            raise HTTPException(
                status_code=422,
                detail="building must be AB1, AB2, AB3, or AB4",
            )

        query = query.filter(
            Room.academic_block.ilike(normalized_block)
        )

    rooms = query.order_by(
        Room.academic_block,
        Room.code,
    ).all()

    now = datetime.utcnow()
    rows = []
    weekday = selected_date.weekday()

    for room in rooms:
        classes = (
            db.query(Timetable)
            .filter(
                Timetable.room_id == room.id,
                Timetable.day_of_week == weekday,
                Timetable.status == "ACTIVE",
                or_(
                    Timetable.effective_from.is_(None),
                    Timetable.effective_from <= day_end,
                ),
                or_(
                    Timetable.effective_to.is_(None),
                    Timetable.effective_to >= day_start,
                ),
            )
            .all()
        )

        bookings = (
            db.query(Booking)
            .filter(
                Booking.room_id == room.id,
                Booking.status.in_([
                    BookingStatus.CONFIRMED,
                    BookingStatus.PENDING_FACULTY_APPROVAL,
                ]),
                Booking.start_time < day_end,
                Booking.end_time > day_start,
            )
            .all()
        )

        holds = (
            db.query(BookingHold)
            .filter(
                BookingHold.room_id == room.id,
                BookingHold.status == "ACTIVE",
                BookingHold.expires_at > now,
                BookingHold.start_time < day_end,
                BookingHold.end_time > day_start,
            )
            .all()
        )

        maintenance = (
            db.query(Maintenance)
            .filter(
                Maintenance.room_id == room.id,
                Maintenance.status != "COMPLETED",
                Maintenance.start_datetime < day_end,
                Maintenance.end_datetime > day_start,
            )
            .all()
        )

        digits = (
            room.code.split("-", 1)[-1]
            if "-" in room.code
            else ""
        )

        for index, (start, end) in enumerate(SLOT_TIMES, start=1):
            slot_start = selected_date.replace(
                hour=int(start[:2]),
                minute=int(start[3:]),
                second=0,
                microsecond=0,
            )
            slot_end = selected_date.replace(
                hour=int(end[:2]),
                minute=int(end[3:]),
                second=0,
                microsecond=0,
            )

            class_busy = any(
                datetime.strptime(
                    entry.start_time, "%H:%M"
                ).time() < slot_end.time()
                and datetime.strptime(
                    entry.end_time, "%H:%M"
                ).time() > slot_start.time()
                for entry in classes
            )

            booking_busy = any(
                entry.start_time < slot_end
                and entry.end_time > slot_start
                for entry in bookings
            )

            hold_busy = any(
                entry.start_time < slot_end
                and entry.end_time > slot_start
                for entry in holds
            )

            maintenance_busy = any(
                entry.start_datetime < slot_end
                and entry.end_datetime > slot_start
                for entry in maintenance
            )

            status = "AVAILABLE"

            if class_busy:
                status = "TIMETABLE_OCCUPIED"
            elif booking_busy:
                status = "BOOKING_OCCUPIED"
            elif hold_busy:
                status = "HELD"
            elif maintenance_busy:
                status = "MAINTENANCE"

            rows.append({
                "classroom_id": room.code,
                "building": (
                    room.academic_block
                    or (room.building.code if room.building else "")
                ),
                "floor": (
                    int(digits[0])
                    if len(digits) == 3 and digits.isdigit()
                    else None
                ),
                "class_number": (
                    digits[-2:]
                    if len(digits) == 3 and digits.isdigit()
                    else None
                ),
                "room_id": room.id,
                "capacity": room.capacity,
                "date": date_value,
                "day_of_week": weekday,
                "day_name": selected_date.strftime("%A"),
                "slot": index,
                "start_time": start,
                "end_time": end,
                "status": status,
                "is_free": status == "AVAILABLE",
            })

    return rows


@router.get("/free-slots")
def classroom_free_slots(
    date: str = Query(...),
    building: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    selected_date = _read_date(date, "date")

    return {
        "date": date,
        "day_name": selected_date.strftime("%A"),
        "building": building,
        "slots": build_free_slot_rows(db, date, building),
    }


@router.get("/free-slots.csv")
def export_classroom_free_slots(
    date: str = Query(...),
    building: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = build_free_slot_rows(db, date, building)

    columns = [
        "classroom_id",
        "building",
        "floor",
        "class_number",
        "room_id",
        "capacity",
        "date",
        "day_of_week",
        "day_name",
        "slot",
        "start_time",
        "end_time",
        "status",
        "is_free",
    ]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

    filename = (
        f"classroom_free_slots_{date}_{building or 'all'}.csv"
    )

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )