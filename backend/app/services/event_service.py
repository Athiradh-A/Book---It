import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import EventRequest, EventProposalDetails, EventMeetingRequest, ApprovalStep, Booking, BookingHold, BookingStatus, Notification, RegistrationEvent, Room
from app.schemas.events import EventRequestCreate, ApprovalDecision
from app.schemas.bookings import AvailabilityRequest
from app.services.availability_service import AvailabilityService
from app.core.event_workflow import require_stage_role, can_resubmit

DETAIL_FIELDS = {
    "department", "responsible_faculty", "discipline_faculty", "infrastructure_needs",
    "catering_needs", "vehicle_needs", "accommodation_needs", "funding_source",
    "funding_amount", "risk_assessment"
}

class EventService:
    @staticmethod
    def create_event_request(db: Session, user_id: int, event_in: EventRequestCreate):
        if event_in.end_time <= event_in.start_time:
            raise HTTPException(422, "Event end time must be after its start time")
        req = AvailabilityRequest(
            date=event_in.date, start_time=event_in.start_time, end_time=event_in.end_time,
            required_capacity=event_in.expected_attendees, required_equipment_ids=[]
        )
        conflict = AvailabilityService.check_room_availability(db, event_in.room_id, req)
        if not conflict.is_available:
            raise HTTPException(status_code=409, detail=f"Hall unavailable: {conflict.details or conflict.conflict_type}")
        payload = event_in.model_dump()
        details = {key: payload.pop(key, None) for key in DETAIL_FIELDS}
        event = EventRequest(
            requested_by=user_id, room_id=payload["room_id"], event_name=payload["event_name"],
            event_category=payload["event_category"], description=payload["description"],
            date=payload["date"], start_time=payload["start_time"], end_time=payload["end_time"],
            expected_attendees=payload["expected_attendees"], status=BookingStatus.PENDING_FACULTY_APPROVAL,
            current_approval_level=1
        )
        db.add(event)
        db.flush()
        db.add(EventProposalDetails(event_request_id=event.id, details_json=json.dumps(details, default=str)))
        db.add(Notification(user_id=user_id, message=f"Your event request {event.event_name} has been submitted."))
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def process_approval(db: Session, event_id: int, approver_id: int, decision_in: ApprovalDecision):
        event = db.query(EventRequest).filter(EventRequest.id == event_id).with_for_update().first()
        if not event:
            raise HTTPException(status_code=404, detail="Event request not found")
        decision = decision_in.decision.upper()
        if decision == "MEETING_REQUESTED":
            if not decision_in.comment.strip():
                raise HTTPException(422, "A meeting reason is required")
            meeting = EventMeetingRequest(
                event_request_id=event.id, requested_by=approver_id,
                approval_level=event.current_approval_level, reason=decision_in.comment,
                preferred_at=decision_in.preferred_meeting_at
            )
            db.add(meeting)
            db.add(ApprovalStep(event_request_id=event.id, level=event.current_approval_level, approver_id=approver_id, decision=decision, comment=decision_in.comment))
            db.add(Notification(user_id=event.requested_by, message=f"A meeting was requested for your event proposal: {event.event_name}."))
            db.commit()
            db.refresh(event)
            return event

        if decision not in {"APPROVED", "REJECTED", "RETURNED"}:
            raise HTTPException(422, "Decision must be APPROVED, REJECTED, RETURNED, or MEETING_REQUESTED")

        db.add(ApprovalStep(event_request_id=event.id, level=event.current_approval_level, approver_id=approver_id, decision=decision, comment=decision_in.comment))
        if decision in {"REJECTED", "RETURNED"}:
            event.status = BookingStatus.REJECTED if decision == "REJECTED" else BookingStatus.RETURNED_FOR_CHANGES
            EventService._release_hall_hold(db, event)
            note = f": {decision_in.comment}" if decision_in.comment else ""
            db.add(Notification(user_id=event.requested_by, message=f"Your event proposal {event.event_name} was {decision.lower().replace('_', ' ')}{note}"))
        elif event.current_approval_level == 1:
            event.current_approval_level = 2
            event.status = BookingStatus.PENDING_WELFARE_APPROVAL
        elif event.current_approval_level == 2:
            # Serialize competing hall-hold attempts on the shared room row.
            room = db.query(Room).filter(Room.id == event.room_id).with_for_update().first()
            if not room:
                db.rollback()
                raise HTTPException(404, "Hall not found")
            req = AvailabilityRequest(date=event.date, start_time=event.start_time, end_time=event.end_time, required_capacity=event.expected_attendees or 1, required_equipment_ids=[])
            conflict = AvailabilityService.check_room_availability(db, event.room_id, req)
            if not conflict.is_available:
                db.rollback()
                raise HTTPException(409, f"Cannot place the 48-hour hall hold: {conflict.details or conflict.conflict_type}")
            hold = BookingHold(room_id=event.room_id, user_id=event.requested_by, date=event.date, start_time=event.start_time, end_time=event.end_time, expires_at=datetime.utcnow()+timedelta(hours=48), status="ACTIVE")
            db.add(hold)
            event.current_approval_level = 3
            event.status = BookingStatus.PENDING_DIRECTOR_APPROVAL
        elif event.current_approval_level == 3:
            room = db.query(Room).filter(Room.id == event.room_id).with_for_update().first()
            if not room:
                db.rollback()
                raise HTTPException(404, "Hall not found")
            active_hold = db.query(BookingHold).filter(
                BookingHold.room_id == event.room_id, BookingHold.user_id == event.requested_by,
                BookingHold.start_time == event.start_time, BookingHold.end_time == event.end_time,
                BookingHold.status == "ACTIVE", BookingHold.expires_at > datetime.utcnow()
            ).first()
            if not active_hold:
                req = AvailabilityRequest(date=event.date, start_time=event.start_time, end_time=event.end_time, required_capacity=event.expected_attendees or 1, required_equipment_ids=[])
                conflict = AvailabilityService.check_room_availability(db, event.room_id, req)
                if not conflict.is_available:
                    db.rollback()
                    raise HTTPException(409, f"The hall hold expired and the room is no longer available: {conflict.details or conflict.conflict_type}")
                db.add(BookingHold(room_id=event.room_id, user_id=event.requested_by, date=event.date, start_time=event.start_time, end_time=event.end_time, expires_at=datetime.utcnow()+timedelta(hours=48), status="ACTIVE"))
            event.current_approval_level = 4
            event.status = BookingStatus.PENDING_EVENTS_APPROVAL
        elif event.current_approval_level == 4:
            EventService._convert_to_booking(db, event, approver_id)
            event.status = BookingStatus.CONFIRMED
            db.add(Notification(user_id=event.requested_by, message=f"Your event proposal {event.event_name} is fully approved and confirmed. It is now available for student registration."))
        else:
            db.rollback()
            raise HTTPException(409, "This proposal is not in a valid approval stage")
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def resubmit_event(db: Session, event_id: int, requester_id: int, event_in: EventRequestCreate):
        """Allow only the owner to resubmit a returned proposal; preserve old approval history."""
        event = db.query(EventRequest).filter(EventRequest.id == event_id).with_for_update().first()
        if not event or event.requested_by != requester_id:
            raise HTTPException(status_code=404, detail="Your event proposal was not found")
        if not can_resubmit(event.status.value if hasattr(event.status, "value") else str(event.status)):
            raise HTTPException(status_code=409, detail="Only proposals returned for changes can be resubmitted")
        if event_in.end_time <= event_in.start_time:
            raise HTTPException(status_code=422, detail="Event end time must be after its start time")
        req = AvailabilityRequest(date=event_in.date, start_time=event_in.start_time, end_time=event_in.end_time, required_capacity=event_in.expected_attendees, required_equipment_ids=[])
        conflict = AvailabilityService.check_room_availability(db, event_in.room_id, req)
        if not conflict.is_available:
            raise HTTPException(status_code=409, detail=f"Hall unavailable: {conflict.details or conflict.conflict_type}")
        payload = event_in.model_dump()
        details = {key: payload.pop(key, None) for key in DETAIL_FIELDS}
        event.room_id = payload["room_id"]
        event.event_name = payload["event_name"]
        event.event_category = payload.get("event_category")
        event.description = payload.get("description")
        event.date = payload["date"]
        event.start_time = payload["start_time"]
        event.end_time = payload["end_time"]
        event.expected_attendees = payload["expected_attendees"]
        event.current_approval_level = 1
        event.status = BookingStatus.PENDING_FACULTY_APPROVAL
        detail = db.query(EventProposalDetails).filter(EventProposalDetails.event_request_id == event.id).first()
        if detail:
            detail.details_json = json.dumps(details, default=str)
        else:
            db.add(EventProposalDetails(event_request_id=event.id, details_json=json.dumps(details, default=str)))
        db.add(ApprovalStep(event_request_id=event.id, level=1, approver_id=requester_id, decision="RESUBMITTED", comment="Requester resubmitted returned proposal"))
        db.add(Notification(user_id=requester_id, message=f"Your event proposal {event.event_name} was resubmitted to Faculty for review."))
        db.commit(); db.refresh(event)
        return event

    @staticmethod
    def _release_hall_hold(db: Session, event: EventRequest):
        holds = db.query(BookingHold).filter(
            BookingHold.room_id == event.room_id, BookingHold.user_id == event.requested_by,
            BookingHold.start_time == event.start_time, BookingHold.end_time == event.end_time,
            BookingHold.status == "ACTIVE"
        ).all()
        for hold in holds:
            hold.status = "EXPIRED"

    @staticmethod
    def _convert_to_booking(db: Session, event: EventRequest, publisher_id: int):
        hold = db.query(BookingHold).filter(
            BookingHold.room_id == event.room_id, BookingHold.user_id == event.requested_by,
            BookingHold.start_time == event.start_time, BookingHold.end_time == event.end_time,
            BookingHold.status == "ACTIVE", BookingHold.expires_at > datetime.utcnow()
        ).with_for_update().first()
        if not hold:
            raise HTTPException(409, "The 48-hour hall hold has expired. The proposal must be reviewed again.")
        room = db.query(Room).filter(Room.id == event.room_id).with_for_update().first()
        if not room:
            raise HTTPException(404, "Hall not found")
        req = AvailabilityRequest(date=event.date, start_time=event.start_time, end_time=event.end_time, required_capacity=event.expected_attendees or 1, required_equipment_ids=[])
        conflict = AvailabilityService.check_room_availability(db, event.room_id, req, ignore_hold_id=hold.id)
        if not conflict.is_available:
            raise HTTPException(409, f"Final hall conflict check failed: {conflict.details or conflict.conflict_type}")
        booking = Booking(
            room_id=event.room_id, requester_id=event.requested_by, booking_type="HALL",
            event_request_id=event.id,
            date=event.date, start_time=event.start_time, end_time=event.end_time,
            status=BookingStatus.CONFIRMED, purpose=event.event_name,
            expected_attendees=event.expected_attendees, confirmed_at=datetime.utcnow()
        )
        hold.status = "CONVERTED"
        db.add(booking)

        room = db.query(Room).filter(Room.id == event.room_id).first()
        registration_event = RegistrationEvent(
            faculty_id=publisher_id,
            room_id=event.room_id,
            name=event.event_name,
            description=event.description,
            starts_at=event.start_time,
            registration_deadline=event.start_time,
            capacity=room.capacity if room and room.capacity else (event.expected_attendees or 1),
            published=True
        )
        db.add(registration_event)
