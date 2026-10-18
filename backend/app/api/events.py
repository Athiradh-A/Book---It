from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_roles, require_role
from app.schemas.events import EventRequestCreate, EventRequestOut, ApprovalDecision, NotificationOut
from app.services.event_service import EventService
from app.models.models import EventRequest, Notification, BookingStatus, Role, UserRole

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("/request", response_model=EventRequestOut, dependencies=[Depends(require_role(["STUDENT"]))])
def request_event(event_in: EventRequestCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return EventService.create_event_request(db, user.id, event_in)


@router.put("/{event_id}/resubmit", response_model=EventRequestOut)
def resubmit_event(event_id: int, event_in: EventRequestCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return EventService.resubmit_event(db, event_id, user.id, event_in)

@router.get("/my", response_model=List[EventRequestOut])
def my_event_requests(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(EventRequest).filter(EventRequest.requested_by == user.id).order_by(EventRequest.id.desc()).all()

@router.get("/pending", response_model=List[EventRequestOut], dependencies=[Depends(require_role(["FACULTY", "WELFARE", "DIRECTOR", "EVENTS"]))])
def pending_approvals(db: Session = Depends(get_db), user=Depends(get_current_user), current_roles=Depends(get_current_user_roles)):
    # Approval queues are stage-specific even though ordinary features are inherited.
    roles = set(current_roles)
    stages = {
        "FACULTY": BookingStatus.PENDING_FACULTY_APPROVAL,
        "WELFARE": BookingStatus.PENDING_WELFARE_APPROVAL,
        "DIRECTOR": BookingStatus.PENDING_DIRECTOR_APPROVAL,
        "EVENTS": BookingStatus.PENDING_EVENTS_APPROVAL,
    }
    statuses = [value for role, value in stages.items() if role in roles]
    if not statuses:
        return []
    return db.query(EventRequest).filter(EventRequest.status.in_(statuses)).order_by(EventRequest.id).all()

@router.post("/approve")
def approve_event(event_id: int, decision: ApprovalDecision, db: Session = Depends(get_db), user=Depends(get_current_user), current_roles=Depends(get_current_user_roles)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event request not found")
    # Never use inherited roles for decisions: only the assigned role for the
    # current stage may approve, return, reject, or request a meeting.
    roles = set(current_roles)
    required = {
        BookingStatus.PENDING_FACULTY_APPROVAL: "FACULTY",
        BookingStatus.PENDING_WELFARE_APPROVAL: "WELFARE",
        BookingStatus.PENDING_DIRECTOR_APPROVAL: "DIRECTOR",
        BookingStatus.PENDING_EVENTS_APPROVAL: "EVENTS",
    }.get(event.status)
    if required is None or required not in roles:
        raise HTTPException(status_code=403, detail="Your role cannot decide this approval stage")
    return EventService.process_approval(db, event_id, user.id, decision)

@router.get("/notifications", response_model=List[NotificationOut])
def my_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
