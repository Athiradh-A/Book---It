from datetime import datetime, time, timedelta
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import (
    Booking,
    BookingHold,
    BookingStatus,
    Maintenance,
    Room,
    RoomEquipment,
    Timetable,
)
from app.schemas.bookings import AvailabilityRequest, ConflictInfo


class AvailabilityService:
    @staticmethod
    def expire_stale_holds(db: Session) -> int:
        now = datetime.utcnow()
        count = (
            db.query(BookingHold)
            .filter(
                BookingHold.status == "ACTIVE",
                BookingHold.expires_at <= now,
            )
            .update(
                {BookingHold.status: "EXPIRED"},
                synchronize_session=False,
            )
        )
        if count:
            db.flush()
        return count

    @staticmethod
    def check_room_availability(
        db: Session,
        room_id: int,
        req: AvailabilityRequest,
        ignore_hold_id: Optional[int] = None,
        ignore_booking_id: Optional[int] = None,
    ) -> ConflictInfo:
        AvailabilityService.expire_stale_holds(db)

        room = db.query(Room).filter(Room.id == room_id).first()
        if room is None:
            return ConflictInfo(
                room_id=room_id,
                code="UNKNOWN",
                is_available=False,
                conflict_type="NOT_FOUND",
                details="Room does not exist",
            )

        room_type = (room.room_type or "").strip().upper()

        # Every classroom must have a capacity from 40 through 80.
        if room_type == "CLASSROOM" and not 40 <= room.capacity <= 80:
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="INVALID_CAPACITY",
                details=(
                    "Classroom capacity must be between 40 and 80; "
                    f"this room has {room.capacity}."
                ),
            )

        if room.capacity < req.required_capacity:
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="CAPACITY",
                details=(
                    f"Room capacity {room.capacity} is less than "
                    f"required {req.required_capacity}."
                ),
            )

        if req.room_type and room_type != req.room_type.strip().upper():
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="ROOM_TYPE",
                details=(
                    f"Room type {room.room_type} does not match "
                    f"required {req.room_type}."
                ),
            )

        assigned_equipment = {
            equipment_id
            for (equipment_id,) in (
                db.query(RoomEquipment.equipment_id)
                .filter(RoomEquipment.room_id == room_id)
                .all()
            )
        }

        for equipment_id in req.required_equipment_ids:
            if equipment_id not in assigned_equipment:
                return ConflictInfo(
                    room_id=room.id,
                    code=room.code,
                    is_available=False,
                    conflict_type="EQUIPMENT",
                    details=(
                        f"Room is missing required equipment ID "
                        f"{equipment_id}."
                    ),
                )

        # Python weekday numbering: Monday=0, Sunday=6.
        request_date = (
            req.date.date()
            if isinstance(req.date, datetime)
            else req.date
        )
        day_start = datetime.combine(request_date, time.min)
        day_end = (
            day_start
            + timedelta(days=1)
            - timedelta(microseconds=1)
        )
        weekday = request_date.weekday()

        timetable_entries = (
            db.query(Timetable)
            .filter(
                Timetable.room_id == room_id,
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

        req_start_time = req.start_time.time()
        req_end_time = req.end_time.time()

        for entry in timetable_entries:
            try:
                class_start = datetime.strptime(
                    entry.start_time.strip(), "%H:%M"
                ).time()
                class_end = datetime.strptime(
                    entry.end_time.strip(), "%H:%M"
                ).time()
            except (ValueError, AttributeError):
                return ConflictInfo(
                    room_id=room.id,
                    code=room.code,
                    is_available=False,
                    conflict_type="TIMETABLE_DATA_ERROR",
                    details=(
                        "Invalid timetable time for this room: "
                        f"{entry.start_time} - {entry.end_time}."
                    ),
                )

            if req_start_time < class_end and req_end_time > class_start:
                return ConflictInfo(
                    room_id=room.id,
                    code=room.code,
                    is_available=False,
                    conflict_type="TIMETABLE",
                    details=(
                        "Official timetable conflict: "
                        f"{entry.start_time} - {entry.end_time}."
                    ),
                )

        booking_query = db.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.status.in_([
                BookingStatus.CONFIRMED,
                BookingStatus.PENDING_FACULTY_APPROVAL,
            ]),
            Booking.start_time < req.end_time,
            Booking.end_time > req.start_time,
        )

        if ignore_booking_id is not None:
            booking_query = booking_query.filter(
                Booking.id != ignore_booking_id
            )

        booking = booking_query.first()
        if booking:
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="BOOKING",
                details=(
                    f"Booking conflict: {booking.start_time} "
                    f"to {booking.end_time}."
                ),
            )

        hold_query = db.query(BookingHold).filter(
            BookingHold.room_id == room_id,
            BookingHold.status == "ACTIVE",
            BookingHold.expires_at > datetime.utcnow(),
            BookingHold.start_time < req.end_time,
            BookingHold.end_time > req.start_time,
        )

        if ignore_hold_id is not None:
            hold_query = hold_query.filter(
                BookingHold.id != ignore_hold_id
            )

        if hold_query.first():
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="HOLD",
                details="Room is temporarily held by another user.",
            )

        maintenance = db.query(Maintenance).filter(
            Maintenance.room_id == room_id,
            Maintenance.status != "COMPLETED",
            Maintenance.start_datetime < req.end_time,
            Maintenance.end_datetime > req.start_time,
        ).first()

        if maintenance:
            return ConflictInfo(
                room_id=room.id,
                code=room.code,
                is_available=False,
                conflict_type="MAINTENANCE",
                details=(
                    "Room is under maintenance: "
                    f"{maintenance.reason or 'No reason specified'}."
                ),
            )

        return ConflictInfo(
            room_id=room.id,
            code=room.code,
            is_available=True,
        )

    @staticmethod
    def find_available_rooms(
        db: Session,
        req: AvailabilityRequest,
    ) -> List[ConflictInfo]:
        query = db.query(Room).filter(Room.is_active.is_(True))

        if req.room_type:
            query = query.filter(
                Room.room_type.ilike(req.room_type.strip())
            )

        if req.academic_block:
            query = query.filter(
                Room.academic_block.ilike(req.academic_block.strip())
            )

        # Retain compatibility with existing callers. The updated
        # frontend does not send building_id.
        if req.building_id:
            query = query.filter(Room.building_id == req.building_id)

        # Exclude classroom inventory records whose capacities are invalid.
        query = query.filter(
            or_(
                Room.room_type.is_(None),
                Room.room_type.notilike("CLASSROOM"),
                (Room.capacity >= 40) & (Room.capacity <= 80),
            )
        )

        rooms = query.order_by(
            Room.academic_block,
            Room.code,
        ).all()

        return [
            AvailabilityService.check_room_availability(
                db, room.id, req
            )
            for room in rooms
        ]

    @staticmethod
    def recommend_alternatives(
        db: Session,
        req: AvailabilityRequest,
        limit: int = 3,
    ) -> List[ConflictInfo]:
        checks = AvailabilityService.find_available_rooms(db, req)

        available = [
            room for room in checks if room.is_available
        ]
        if available:
            return available[:limit]

        priority = {
            "TIMETABLE": 100,
            "MAINTENANCE": 100,
            "BOOKING": 50,
            "HOLD": 10,
            "CAPACITY": 20,
            "INVALID_CAPACITY": 30,
        }

        checks.sort(
            key=lambda room: priority.get(
                room.conflict_type or "", 0
            )
        )
        return checks[:limit]