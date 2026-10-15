from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.schemas.events import EventRequestCreate, EventRequestOut, ApprovalDecision, NotificationOut
from app.services.event_service import EventService
from app.models.models import EventRequest, Notification, BookingStatus, Role, UserRole

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("/request", response_model=EventRequestOut)
def request_event(event_in: EventRequestCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return EventService.create_event_request(db, user.id, event_in)

@router.get("/my", response_model=List[EventRequestOut])
def my_event_requests(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(EventRequest).filter(EventRequest.requested_by == user.id).order_by(EventRequest.id.desc()).all()

@router.get("/pending", response_model=List[EventRequestOut], dependencies=[Depends(require_role(["FACULTY", "WELFARE", "DIRECTOR", "EVENTS", "ADMIN"]))])
def pending_approvals(db: Session = Depends(get_db), user=Depends(get_current_user)):
    roles = {name for (name,) in db.query(Role.name).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()}
    stages = {
        "FACULTY": BookingStatus.PENDING_FACULTY_APPROVAL,
        "WELFARE": BookingStatus.PENDING_WELFARE_APPROVAL,
        "DIRECTOR": BookingStatus.PENDING_DIRECTOR_APPROVAL,
        "EVENTS": BookingStatus.PENDING_EVENTS_APPROVAL,
    }
    statuses = [value for role, value in stages.items() if role in roles]
    if "ADMIN" in roles:
        statuses = list(stages.values())
    if not statuses:
        return []
    return db.query(EventRequest).filter(EventRequest.status.in_(statuses)).order_by(EventRequest.id).all()

@router.post("/approve")
def approve_event(event_id: int, decision: ApprovalDecision, db: Session = Depends(get_db), user=Depends(get_current_user)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event request not found")
    roles = {name for (name,) in db.query(Role.name).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()}
    required = {
        BookingStatus.PENDING_FACULTY_APPROVAL: "FACULTY",
        BookingStatus.PENDING_WELFARE_APPROVAL: "WELFARE",
        BookingStatus.PENDING_DIRECTOR_APPROVAL: "DIRECTOR",
        BookingStatus.PENDING_EVENTS_APPROVAL: "EVENTS",
    }.get(event.status)
    if "ADMIN" not in roles and required not in roles:
        raise HTTPException(status_code=403, detail="Your role cannot decide this approval stage")
    return EventService.process_approval(db, event_id, user.id, decision)

@router.get("/notifications", response_model=List[NotificationOut])
def my_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
