from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Event, StudentProfile
from app.schemas.schemas import EventRead, EligibilityCheckResult
from app.services.eligibility import evaluate_student_eligibility

router = APIRouter(prefix="/events", tags=["Upcoming Events Discovery"])

def compute_event_current_status(evt: Event) -> str:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if evt.publication_status == "CANCELLED":
        return "Cancelled"
    if evt.publication_status == "COMPLETED" or (evt.end_datetime and evt.end_datetime.replace(tzinfo=None) < now):
        return "Completed"
    if evt.publication_status != "PUBLISHED":
        return "Unpublished"

    if not evt.is_registration_required or evt.capacity_type == "NONE_INFORMATIONAL":
        return "Informational"

    if evt.capacity_type == "LIMITED" and evt.remaining_seats is not None and evt.remaining_seats <= 0:
        return "Registration Full"

    if evt.registration_open_datetime:
        open_dt = evt.registration_open_datetime.replace(tzinfo=None)
        if now < open_dt:
            return "Registration Not Open"

    if evt.registration_close_datetime:
        close_dt = evt.registration_close_datetime.replace(tzinfo=None)
        if now > close_dt:
            return "Registration Closed"

    return "Registration Open"

@router.get("", response_model=List[EventRead])
def list_published_events(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    # Rule: Only events authorized and published by the main portal appear in discovery.
    # Draft or unapproved events are NOT exposed.
    query = db.query(Event).filter(Event.publication_status.in_(["PUBLISHED", "CANCELLED", "COMPLETED"]))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Event.title.ilike(search_pattern)) | 
            (Event.description.ilike(search_pattern)) |
            (Event.venue.ilike(search_pattern))
        )

    if department:
        query = query.filter(Event.organizing_department == department)

    if category:
        query = query.filter(Event.event_category == category)

    events = query.order_by(Event.start_datetime.asc()).all()
    results = []

    for evt in events:
        current_st = compute_event_current_status(evt)
        if status_filter and current_st.lower() != status_filter.lower():
            continue
        
        evt_schema = EventRead.model_validate(evt)
        evt_schema.current_status = current_st
        results.append(evt_schema)

    return results

@router.get("/{event_id}", response_model=EventRead)
def get_event_details(event_id: int, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt or evt.publication_status not in ["PUBLISHED", "CANCELLED", "COMPLETED"]:
        raise HTTPException(status_code=404, detail="Event not found or not published.")

    evt_schema = EventRead.model_validate(evt)
    evt_schema.current_status = compute_event_current_status(evt)
    return evt_schema

@router.get("/{event_id}/check-eligibility", response_model=EligibilityCheckResult)
def check_student_eligibility(event_id: int, student_profile_id: str, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found.")

    profile = db.get(StudentProfile, student_profile_id)
    return evaluate_student_eligibility(profile, evt.eligibility_rule)
