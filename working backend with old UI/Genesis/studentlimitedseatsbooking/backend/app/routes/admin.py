from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Event, EligibilityRule, StudentProfile
from app.schemas.schemas import (
    EventCreate, EventUpdate, EventRead, StudentProfileRead, StudentProfileBase, EligibilityRuleCreate, EligibilityRuleRead
)
from app.services.calendar_sync import sync_event_to_calendar

router = APIRouter(prefix="/admin", tags=["Event Administration & Portal Integration"])

@router.post("/events", response_model=EventRead)
def create_event_admin(payload: EventCreate, db: Session = Depends(get_db)):
    rem_seats = payload.total_capacity if payload.capacity_type == "LIMITED" else None

    evt = Event(
        title=payload.title,
        description=payload.description,
        organizing_department=payload.organizing_department,
        event_category=payload.event_category,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        venue=payload.venue,
        faculty_contact=payload.faculty_contact,
        poster_url=payload.poster_url,
        publication_status=payload.publication_status,
        is_registration_required=payload.is_registration_required,
        capacity_type=payload.capacity_type,
        total_capacity=payload.total_capacity,
        remaining_seats=rem_seats,
        registration_open_datetime=payload.registration_open_datetime,
        registration_close_datetime=payload.registration_close_datetime,
        allow_cancellation=payload.allow_cancellation,
        cancellation_deadline=payload.cancellation_deadline
    )
    db.add(evt)
    db.flush()

    # Configure Eligibility Rule if provided
    if payload.eligibility_rule:
        rule = EligibilityRule(
            event_id=evt.id,
            is_open_to_all=payload.eligibility_rule.is_open_to_all
        )
        rule.allowed_programmes = payload.eligibility_rule.allowed_programmes
        rule.allowed_departments = payload.eligibility_rule.allowed_departments
        rule.allowed_academic_years = payload.eligibility_rule.allowed_academic_years
        rule.allowed_batches = payload.eligibility_rule.allowed_batches
        db.add(rule)

    db.commit()
    db.refresh(evt)

    # Automatically trigger Academic Calendar Sync
    sync_event_to_calendar(db, evt)

    return evt

@router.patch("/events/{event_id}", response_model=EventRead)
def update_event_admin(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found.")

    update_data = payload.model_dump(exclude_unset=True)
    rule_data = update_data.pop("eligibility_rule", None)

    for field, val in update_data.items():
        setattr(evt, field, val)

    # Adjust remaining seats if capacity changed
    if "total_capacity" in update_data and evt.capacity_type == "LIMITED":
        new_cap = update_data["total_capacity"]
        if new_cap is not None:
            diff = new_cap - (evt.total_capacity or 0)
            evt.remaining_seats = max(0, (evt.remaining_seats or 0) + diff)
            evt.total_capacity = new_cap

    if rule_data:
        rule = evt.eligibility_rule
        if not rule:
            rule = EligibilityRule(event_id=evt.id)
            db.add(rule)
        
        if "is_open_to_all" in rule_data:
            rule.is_open_to_all = rule_data["is_open_to_all"]
        if "allowed_programmes" in rule_data:
            rule.allowed_programmes = rule_data["allowed_programmes"]
        if "allowed_departments" in rule_data:
            rule.allowed_departments = rule_data["allowed_departments"]
        if "allowed_academic_years" in rule_data:
            rule.allowed_academic_years = rule_data["allowed_academic_years"]
        if "allowed_batches" in rule_data:
            rule.allowed_batches = rule_data["allowed_batches"]

    db.commit()
    db.refresh(evt)

    # Automatic Academic Calendar Sync
    sync_event_to_calendar(db, evt)

    return evt

@router.get("/students", response_model=List[StudentProfileRead])
def list_student_profiles(db: Session = Depends(get_db)):
    return db.query(StudentProfile).all()

@router.post("/students", response_model=StudentProfileRead)
def upsert_student_profile(profile_data: StudentProfileBase, db: Session = Depends(get_db)):
    prof = db.get(StudentProfile, profile_data.id)
    if not prof:
        prof = StudentProfile(
            id=profile_data.id,
            user_id=profile_data.user_id,
            full_name=profile_data.full_name,
            email=profile_data.email,
            programme=profile_data.programme,
            department=profile_data.department,
            current_academic_year=profile_data.current_academic_year,
            graduating_batch=profile_data.graduating_batch,
            verification_status=profile_data.verification_status
        )
        db.add(prof)
    else:
        prof.full_name = profile_data.full_name
        prof.email = profile_data.email
        prof.programme = profile_data.programme
        prof.department = profile_data.department
        prof.current_academic_year = profile_data.current_academic_year
        prof.graduating_batch = profile_data.graduating_batch
        prof.verification_status = profile_data.verification_status

    db.commit()
    db.refresh(prof)
    return prof


@router.post("/events/{event_id}/eligibility", response_model=EligibilityRuleRead)
def configure_event_eligibility(event_id: int, payload: EligibilityRuleCreate, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found.")
    
    rule = evt.eligibility_rule
    if not rule:
        rule = EligibilityRule(event_id=evt.id)
        db.add(rule)
    
    rule.is_open_to_all = payload.is_open_to_all
    rule.allowed_programmes = payload.allowed_programmes
    rule.allowed_departments = payload.allowed_departments
    rule.allowed_academic_years = payload.allowed_academic_years
    rule.allowed_batches = payload.allowed_batches
    db.commit()
    db.refresh(rule)
    return rule

@router.post("/events/{event_id}/publish", response_model=EventRead)
def set_event_publish_status(
    event_id: int,
    is_published: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found.")
    
    if status is not None:
        evt.publication_status = status
    elif is_published is not None:
        evt.publication_status = "PUBLISHED" if is_published else "UNPUBLISHED"
        
    db.commit()
    db.refresh(evt)
    sync_event_to_calendar(db, evt)
    return evt


@router.post("/events/{event_id}/reset-seats", response_model=EventRead)
def reset_event_seats(event_id: int, db: Session = Depends(get_db)):
    evt = db.get(Event, event_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found.")
    
    db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.registration_status == "CONFIRMED"
    ).update({"registration_status": "CANCELLED"}, synchronize_session=False)

    evt.remaining_seats = evt.total_capacity
    db.commit()
    db.refresh(evt)
    sync_event_to_calendar(db, evt)
    return evt
