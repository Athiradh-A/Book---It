from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.schemas.events import EventRequestCreate, EventRequestOut, ApprovalDecision, NotificationOut
from app.services.event_service import EventService
from app.models.models import EventRequest, Notification, BookingStatus

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("/request", response_model=EventRequestOut)
def request_event(event_in: EventRequestCreate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    return EventService.create_event_request(db, user.id, event_in)

@router.get("/my", response_model=List[EventRequestOut])
def my_event_requests(db: Session = Depends(get_db), user = Depends(get_current_user)):
    return db.query(EventRequest).filter(EventRequest.requested_by == user.id).all()

@router.get("/pending", response_model=List[EventRequestOut], dependencies=[Depends(require_role(["FACULTY", "WELFARE", "ADMIN"]))])
def pending_approvals(db: Session = Depends(get_db), user = Depends(get_current_user)):
    return db.query(EventRequest).filter(
        EventRequest.status.in_([
            BookingStatus.PENDING_FACULTY_APPROVAL, 
            BookingStatus.PENDING_WELFARE_APPROVAL, 
            BookingStatus.PENDING_DIRECTOR_APPROVAL
        ])
    ).all()

@router.post("/approve")
def approve_event(event_id: int, decision: ApprovalDecision, db: Session = Depends(get_db), user = Depends(get_current_user)):
    return EventService.process_approval(db, event_id, user.id, decision)

@router.get("/notifications", response_model=List[NotificationOut])
def my_notifications(db: Session = Depends(get_db), user = Depends(get_current_user)):
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
