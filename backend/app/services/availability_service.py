from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Room, Timetable, Booking, BookingHold, Maintenance, RoomEquipment, BookingStatus
from app.schemas.bookings import AvailabilityRequest, ConflictInfo
from datetime import datetime, time

class AvailabilityService:
    @staticmethod
    def expire_stale_holds(db: Session) -> int:
        count = db.query(BookingHold).filter(
            BookingHold.status == "ACTIVE",
            BookingHold.expires_at <= datetime.utcnow()
        ).update({BookingHold.status: "EXPIRED"}, synchronize_session=False)
        if count:
            db.flush()
        return count

    @staticmethod
    def check_room_availability(db: Session, room_id: int, req: AvailabilityRequest, ignore_hold_id: Optional[int] = None, ignore_booking_id: Optional[int] = None) -> ConflictInfo:
        AvailabilityService.expire_stale_holds(db)
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            return ConflictInfo(room_id=room_id, code="UNKNOWN", is_available=False, conflict_type="NOT_FOUND", details="Room does not exist")

        if room.capacity < req.required_capacity:
            return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="CAPACITY", details=f"Room capacity {room.capacity} is less than required {req.required_capacity}")

        room_eq = db.query(RoomEquipment.equipment_id).filter(RoomEquipment.room_id == room_id).all()
        room_eq_ids = [e[0] for e in room_eq]
        for req_eq_id in req.required_equipment_ids:
            if req_eq_id not in room_eq_ids:
                return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="EQUIPMENT", details=f"Room is missing required equipment ID {req_eq_id}")

        if req.room_type and room.room_type != req.room_type:
            return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="ROOM_TYPE", details=f"Room type {room.room_type} does not match required {req.room_type}")

        day_of_week = req.date.weekday()
        tt_entries = db.query(Timetable).filter(
            Timetable.room_id == room_id,
            Timetable.day_of_week == day_of_week,
            Timetable.status == "ACTIVE",
            Timetable.effective_from <= req.date,
            Timetable.effective_to >= req.date
        ).all()

        req_start_time = req.start_time.time()
        req_end_time = req.end_time.time()

        for tt in tt_entries:
            tt_start = datetime.strptime(tt.start_time, "%H:%M").time()
            tt_end = datetime.strptime(tt.end_time, "%H:%M").time()
            if (req_start_time < tt_end) and (req_end_time > tt_start):
                return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="TIMETABLE", details=f"Official timetable conflict: {tt.start_time} - {tt.end_time}")

        booking_query = db.query(Booking).filter(
            Booking.room_id == room_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING_FACULTY_APPROVAL]),
            Booking.start_time < req.end_time,
            Booking.end_time > req.start_time
        )
        if ignore_booking_id is not None:
            booking_query = booking_query.filter(Booking.id != ignore_booking_id)
        overlapping_bookings = booking_query.first()
        if overlapping_bookings:
            return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="BOOKING", details=f"Confirmed booking conflict: {overlapping_bookings.start_time} to {overlapping_bookings.end_time}")

        hold_query = db.query(BookingHold).filter(
            BookingHold.room_id == room_id,
            BookingHold.status == "ACTIVE",
            BookingHold.expires_at > datetime.utcnow(),
            BookingHold.start_time < req.end_time,
            BookingHold.end_time > req.start_time
        )
        if ignore_hold_id is not None:
            hold_query = hold_query.filter(BookingHold.id != ignore_hold_id)
        overlapping_holds = hold_query.first()
        if overlapping_holds:
            return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="HOLD", details="Room is temporarily held by another user")

        maintenance = db.query(Maintenance).filter(
            Maintenance.room_id == room_id,
            Maintenance.status != "COMPLETED",
            Maintenance.start_datetime < req.end_time,
            Maintenance.end_datetime > req.start_time
        ).first()
        if maintenance:
            return ConflictInfo(room_id=room_id, code=room.code, is_available=False, conflict_type="MAINTENANCE", details=f"Room under maintenance: {maintenance.reason}")

        return ConflictInfo(room_id=room_id, code=room.code, is_available=True)

    @staticmethod
    def find_available_rooms(db: Session, req: AvailabilityRequest) -> List[ConflictInfo]:
        query = db.query(Room).filter(Room.is_active == True)
        if req.academic_block:
            query = query.filter(Room.academic_block == req.academic_block)
        if req.building_id:
            query = query.filter(Room.building_id == req.building_id)
        
        rooms = query.all()
        results = []
        for room in rooms:
            res = AvailabilityService.check_room_availability(db, room.id, req)
            results.append(res)
        return results

    @staticmethod
    def recommend_alternatives(db: Session, req: AvailabilityRequest, limit: int = 3) -> List[ConflictInfo]:
        all_checks = AvailabilityService.find_available_rooms(db, req)
        available = [r for r in all_checks if r.is_available]
        if available:
            return available[:limit]
        weighted_results = []
        for r in all_checks:
            score = 0
            if r.conflict_type == "TIMETABLE": score += 100
            elif r.conflict_type == "MAINTENANCE": score += 100
            elif r.conflict_type == "BOOKING": score += 50
            elif r.conflict_type == "HOLD": score += 10
            elif r.conflict_type == "CAPACITY": score += 20
            weighted_results.append((score, r))
        weighted_results.sort(key=lambda x: x[0])
        return [r for s, r in weighted_results[:limit]]
