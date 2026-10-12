from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import EventRegistration, Event, StudentProfile
from app.schemas.schemas import EventRegistrationCreate, EventRegistrationRead, EventRead
from app.services.booking import register_student_for_event, cancel_student_registration
from app.routes.events import compute_event_current_status

router = APIRouter(prefix="/registrations", tags=["Student Registrations & FCFS Booking"])

@router.post("", response_model=EventRegistrationRead)
def book_seat(req: EventRegistrationCreate, db: Session = Depends(get_db)):
    reg = register_student_for_event(db, event_id=req.event_id, student_profile_id=req.student_profile_id)
    
    # Populate schema with event status
    reg_schema = EventRegistrationRead.model_validate(reg)
    if reg.event:
        evt_schema = EventRead.model_validate(reg.event)
        evt_schema.current_status = compute_event_current_status(reg.event)
        reg_schema.event = evt_schema

    return reg_schema

@router.post("/{registration_id}/cancel", response_model=EventRegistrationRead)
def cancel_registration(
    registration_id: int,
    student_profile_id: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    target_id = student_profile_id or student_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Student ID parameter is required.")
    reg = cancel_student_registration(db, registration_id=registration_id, student_profile_id=target_id)
    
    reg_schema = EventRegistrationRead.model_validate(reg)
    if reg.event:
        evt_schema = EventRead.model_validate(reg.event)
        evt_schema.current_status = compute_event_current_status(reg.event)
        reg_schema.event = evt_schema

    return reg_schema

@router.get("/my-registrations", response_model=List[EventRegistrationRead])
@router.get("/me", response_model=List[EventRegistrationRead])
def list_my_registrations(
    student_profile_id: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    target_id = student_profile_id or student_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Student ID parameter is required.")

    registrations = db.query(EventRegistration).filter(
        EventRegistration.student_profile_id == target_id
    ).order_by(EventRegistration.registration_timestamp.desc()).all()

    results = []
    for reg in registrations:
        reg_schema = EventRegistrationRead.model_validate(reg)
        if reg.event:
            evt_schema = EventRead.model_validate(reg.event)
            evt_schema.current_status = compute_event_current_status(reg.event)
            reg_schema.event = evt_schema
        results.append(reg_schema)

    return results
