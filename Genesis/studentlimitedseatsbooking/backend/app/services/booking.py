import secrets
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Event, StudentProfile, EventRegistration
from app.services.eligibility import evaluate_student_eligibility
from app.services.calendar_sync import sync_event_to_calendar

def make_naive(dt: datetime) -> datetime:
    if dt and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def generate_registration_reference() -> str:
    year = datetime.now().year
    random_hex = secrets.token_hex(3).upper()
    return f"REG-{year}-{random_hex}"

def register_student_for_event(db: Session, event_id: int, student_profile_id: str) -> EventRegistration:
    # Transaction lock for atomic FCFS concurrency protection
    try:
        db.execute(text("BEGIN IMMEDIATE"))
    except Exception:
        pass

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    if event.publication_status != "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed: This event is not officially published."
        )

    profile = db.get(StudentProfile, student_profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student profile missing or unverified. Please contact Academic Registry."
        )

    # Re-evaluate eligibility on backend!
    eligibility = evaluate_student_eligibility(profile, event.eligibility_rule)
    if not eligibility.is_eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Registration Rejected: {eligibility.reason}"
        )

    # Check registration window
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if event.registration_open_datetime:
        reg_open = make_naive(event.registration_open_datetime)
        if now < reg_open:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration for this event opens on {reg_open.strftime('%Y-%m-%d %H:%M')} UTC."
            )

    if event.registration_close_datetime:
        reg_close = make_naive(event.registration_close_datetime)
        if now > reg_close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration for this event has closed."
            )

    # Check duplicate active registration
    existing_reg = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.student_profile_id == student_profile_id,
        EventRegistration.registration_status == "CONFIRMED"
    ).first()
    if existing_reg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already registered for this event (Ref: {existing_reg.registration_reference})."
        )

    # Process FCFS Capacity
    if event.capacity_type == "NONE_INFORMATIONAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is an informational announcement and does not take registrations."
        )

    if event.capacity_type == "LIMITED":
        updated_rows = db.query(Event).filter(
            Event.id == event.id,
            Event.remaining_seats > 0
        ).update(
            {Event.remaining_seats: Event.remaining_seats - 1},
            synchronize_session=False
        )
        if updated_rows == 0:
            sync_event_to_calendar(db, event)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration Full: All available seats for this event have been claimed."
            )

    reg_ref = generate_registration_reference()
    registration = EventRegistration(
        event_id=event.id,
        student_profile_id=profile.id,
        registration_reference=reg_ref,
        registration_status="CONFIRMED",
        registration_timestamp=datetime.now(timezone.utc)
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)

    # Automatic Academic Calendar Sync
    sync_event_to_calendar(db, event)

    return registration


def cancel_student_registration(db: Session, registration_id: int, student_profile_id: str) -> EventRegistration:
    db.execute(text("BEGIN IMMEDIATE"))

    reg = db.get(EventRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found.")

    if reg.student_profile_id != student_profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You can only cancel your own registrations."
        )

    if reg.registration_status == "CANCELLED":
        return reg

    event = db.get(Event, reg.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Associated event not found.")

    if not event.allow_cancellation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancellation is not permitted for this event."
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if event.cancellation_deadline:
        deadline = make_naive(event.cancellation_deadline)
        if now > deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cancellation deadline ({deadline.strftime('%Y-%m-%d %H:%M')}) has passed."
            )

    reg.registration_status = "CANCELLED"
    reg.cancellation_timestamp = datetime.now(timezone.utc)

    # Release seat transactionally
    if event.capacity_type == "LIMITED" and event.remaining_seats is not None:
        event.remaining_seats += 1

    db.commit()
    db.refresh(reg)

    # Automatic Academic Calendar Sync
    sync_event_to_calendar(db, event)

    return reg
