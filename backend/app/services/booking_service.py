from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.models import Room, Booking, BookingHold, BookingStatus
from app.schemas.bookings import HoldRequest, ConfirmRequest
from app.services.availability_service import AvailabilityService, AvailabilityRequest
from datetime import datetime, timedelta
from fastapi import HTTPException, status

class BookingService:
    @staticmethod
    def create_classroom_hold(db: Session, user_id: int, hold_in: HoldRequest):
        # 1. Verify Availability first
        req = AvailabilityRequest(
            date=hold_in.start_time,
            start_time=hold_in.start_time,
            end_time=hold_in.end_time,
            required_capacity=0,
            required_equipment_ids=[]
        )
        
        conflict = AvailabilityService.check_room_availability(db, hold_in.room_id, req)
        if not conflict.is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room unavailable: {conflict.conflict_type} - {conflict.details}"
            )

        # 2. Create the hold
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        db_hold = BookingHold(
            room_id=hold_in.room_id,
            user_id=user_id,
            date=hold_in.start_time,
            start_time=hold_in.start_time,
            end_time=hold_in.end_time,
            expires_at=expires_at,
            status="ACTIVE"
        )
        db.add(db_hold)
        db.commit()
        db.refresh(db_hold)
        return db_hold

    @staticmethod
    def confirm_classroom_booking(db: Session, user_id: int, confirm_in: ConfirmRequest):
        # Lock the hold record to prevent race conditions
        hold = db.query(BookingHold).filter(
            BookingHold.id == confirm_in.hold_id,
            BookingHold.user_id == user_id,
            BookingHold.status == "ACTIVE"
        ).with_for_update().first()

        if not hold:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found or already processed")

        if hold.expires_at < datetime.utcnow():
            hold.status = "EXPIRED"
            db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Hold has expired")

        # RE-CHECK Availability inside the lock
        req = AvailabilityRequest(
            date=hold.date,
            start_time=hold.start_time,
            end_time=hold.end_time,
            required_capacity=confirm_in.expected_attendees,
            required_equipment_ids=[]
        )
        
        conflict = AvailabilityService.check_room_availability(db, hold.room_id, req)
        
        # Filter out "HOLD" conflict if it is the current hold
        if not conflict.is_available and conflict.conflict_type != "HOLD":
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conflict detected: {conflict.details}")

        new_booking = Booking(
            room_id=hold.room_id,
            requester_id=user_id,
            booking_type="CLASSROOM",
            date=hold.date,
            start_time=hold.start_time,
            end_time=hold.end_time,
            status=BookingStatus.CONFIRMED,
            purpose=confirm_in.purpose,
            expected_attendees=confirm_in.expected_attendees,
            confirmed_at=datetime.utcnow()
        )
        
        hold.status = "CONVERTED"
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        return new_booking
