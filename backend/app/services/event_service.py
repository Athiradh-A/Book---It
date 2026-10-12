from sqlalchemy.orm import Session
from app.models.models import EventRequest, ApprovalStep, Booking, BookingStatus, Notification
from app.schemas.events import EventRequestCreate, ApprovalDecision
from app.services.availability_service import AvailabilityService, AvailabilityRequest
from datetime import datetime
from fastapi import HTTPException, status

class EventService:
    @staticmethod
    def create_event_request(db: Session, user_id: int, event_in: EventRequestCreate):
        # 1. Check basic availability (Ignore other pending requests for now as per policy)
        req = AvailabilityRequest(
            date=event_in.date,
            start_time=event_in.start_time,
            end_time=event_in.end_time,
            required_capacity=event_in.expected_attendees,
            required_equipment_ids=[]
        )
        
        conflict = AvailabilityService.check_room_availability(db, event_in.room_id, req)
        if not conflict.is_available and conflict.conflict_type != "HOLD":
            # We allow requests even if there is a HOLD, but not if there is a confirmed booking or timetable
            if conflict.conflict_type in ["BOOKING", "TIMETABLE", "MAINTENANCE"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Room unavailable: {conflict.details}"
                )

        # 2. Create the request
        db_event = EventRequest(
            requested_by=user_id,
            room_id=event_in.room_id,
            event_name=event_in.event_name,
            event_category=event_in.event_category,
            description=event_in.description,
            date=event_in.date,
            start_time=event_in.start_time,
            end_time=event_in.end_time,
            expected_attendees=event_in.expected_attendees,
            status=BookingStatus.PENDING_FACULTY_APPROVAL,
            current_approval_level=1
        )
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        # Create notification for the user
        notification = Notification(user_id=user_id, message=f"Your event request {event_in.event_name} has been submitted.")
        db.add(notification)
        db.commit()
        
        return db_event

    @staticmethod
    def process_approval(db: Session, event_id: int, approver_id: int, decision_in: ApprovalDecision):
        event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event request not found")

        # Record the step
        step = ApprovalStep(
            event_request_id=event.id,
            level=event.current_approval_level,
            approver_id=approver_id,
            decision=decision_in.decision,
            comment=decision_in.comment
        )
        db.add(step)

        if decision_in.decision == "REJECTED":
            event.status = BookingStatus.REJECTED
        elif decision_in.decision == "RETURNED":
            event.status = BookingStatus.RETURNED_FOR_CHANGES
        elif decision_in.decision == "APPROVED":
            # Progress the state machine
            if event.current_approval_level == 1:
                event.status = BookingStatus.PENDING_WELFARE_APPROVAL
                event.current_approval_level = 2
            elif event.current_approval_level == 2:
                # Check if major event policy applies (simplified: category "MAJOR" requires director)
                if event.event_category == "MAJOR":
                    event.status = BookingStatus.PENDING_DIRECTOR_APPROVAL
                    event.current_approval_level = 3
                else:
                    event.status = BookingStatus.CONFIRMED
                    EventService._convert_to_booking(db, event)
            elif event.current_approval_level == 3:
                event.status = BookingStatus.CONFIRMED
                EventService._convert_to_booking(db, event)
        
        db.commit()
        return event

    @staticmethod
    def _convert_to_booking(db: Session, event: EventRequest):
        # Convert approved event into a confirmed booking
        booking = Booking(
            room_id=event.room_id,
            requester_id=event.requested_by,
            booking_type="HALL",
            date=event.date,
            start_time=event.start_time,
            end_time=event.end_time,
            status=BookingStatus.CONFIRMED,
            purpose=event.event_name,
            expected_attendees=event.expected_attendees,
            confirmed_at=datetime.utcnow()
        )
        db.add(booking)
        db.commit()
