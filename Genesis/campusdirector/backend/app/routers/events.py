from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import EventRequest, ApprovalLog, User
from backend.app.schemas import (
    EventRequestCreate, EventRequestRead, ApprovalActionRequest, ApprovalLogRead
)
from backend.app.crud import (
    create_event_request, faculty_approve_event, welfare_approve_event,
    director_direct_decision, director_request_meeting, events_department_approve
)

router = APIRouter(prefix="/api/events", tags=["Event Requests"])

@router.post("", response_model=EventRequestRead)
def create_event(req: EventRequestCreate, db: Session = Depends(get_db)):
    return create_event_request(db, req)

@router.get("", response_model=List[EventRequestRead])
def list_events(
    stage: Optional[str] = None,
    status: Optional[str] = None,
    student_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(EventRequest)
    if stage:
        query = query.filter(EventRequest.current_stage == stage)
    if status:
        query = query.filter(EventRequest.status == status)
    if student_id:
        query = query.filter(EventRequest.student_coordinator_id == student_id)
    return query.order_by(EventRequest.created_at.desc()).all()

@router.get("/{event_id}", response_model=EventRequestRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(EventRequest, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event request not found")
    return event

@router.get("/{event_id}/logs", response_model=List[ApprovalLogRead])
def get_event_approval_logs(event_id: int, db: Session = Depends(get_db)):
    return db.query(ApprovalLog).filter(ApprovalLog.event_request_id == event_id).order_by(ApprovalLog.timestamp.asc()).all()

@router.post("/{event_id}/faculty-approve", response_model=EventRequestRead)
def faculty_approve(event_id: int, body: ApprovalActionRequest, db: Session = Depends(get_db)):
    return faculty_approve_event(db, event_id, actor_id=body.actor_id, comments=body.comments)

@router.post("/{event_id}/welfare-approve", response_model=EventRequestRead)
def welfare_approve(event_id: int, body: ApprovalActionRequest, db: Session = Depends(get_db)):
    return welfare_approve_event(db, event_id, actor_id=body.actor_id, comments=body.comments)

@router.post("/{event_id}/director-direct-decision", response_model=EventRequestRead)
def director_direct_action(event_id: int, body: ApprovalActionRequest, db: Session = Depends(get_db)):
    return director_direct_decision(db, event_id, actor_id=body.actor_id, decision=body.action, comments=body.comments)

@router.post("/{event_id}/director-request-meeting", response_model=EventRequestRead)
def director_request_meeting_action(event_id: int, body: ApprovalActionRequest, db: Session = Depends(get_db)):
    return director_request_meeting(db, event_id, actor_id=body.actor_id, comments=body.comments)

@router.post("/{event_id}/events-dept-approve", response_model=EventRequestRead)
def events_dept_action(event_id: int, body: ApprovalActionRequest, db: Session = Depends(get_db)):
    return events_department_approve(db, event_id, actor_id=body.actor_id, comments=body.comments)
