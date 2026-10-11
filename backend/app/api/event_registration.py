from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.models import RegistrationEvent, EventTicketAllocation, Room
from app.schemas.event_registration import RegistrationEventCreate, TicketHoldCreate, TicketConfirm

router = APIRouter(prefix="/event-registration", tags=["Event registration"])
ACTIVE_TICKET_STATES = ("HELD", "CONFIRMED")

def serialize_event(db: Session, event: RegistrationEvent):
    now = datetime.utcnow()
    active = db.query(EventTicketAllocation).filter(
        EventTicketAllocation.event_id == event.id,
        or_(EventTicketAllocation.status == "CONFIRMED", EventTicketAllocation.expires_at > now),
    )
    room = db.query(Room).filter(Room.id == event.room_id).first() if event.room_id else None
    return {
        "id": event.id, "faculty_id": event.faculty_id, "room_id": event.room_id,
        "name": event.name, "description": event.description, "starts_at": event.starts_at,
        "registration_deadline": event.registration_deadline, "capacity": event.capacity,
        "published": event.published, "applicant_count": active.count(),
        "confirmed_count": active.filter(EventTicketAllocation.status == "CONFIRMED").count(),
        "room_code": room.code if room else None,
    }

@router.get("")
def list_registration_events(db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.models.models import Role, UserRole
    roles = {name for (name,) in db.query(Role.name).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()}
    query = db.query(RegistrationEvent)
    query = query.filter(RegistrationEvent.faculty_id == user.id) if "FACULTY" in roles else query.filter(RegistrationEvent.published.is_(True))
    return [serialize_event(db, event) for event in query.order_by(RegistrationEvent.starts_at).all()]

@router.post("", status_code=201, dependencies=[Depends(require_role(["FACULTY", "ADMIN"]))])
def create_registration_event(payload: RegistrationEventCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.registration_deadline and payload.registration_deadline > payload.starts_at:
        raise HTTPException(422, "Registration deadline must be before the event")
    event = RegistrationEvent(faculty_id=user.id, **payload.model_dump())
    db.add(event); db.commit(); db.refresh(event)
    return serialize_event(db, event)

@router.post("/{event_id}/hold", status_code=201, dependencies=[Depends(require_role(["STUDENT"]))])
def hold_ticket(event_id: int, payload: TicketHoldCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    event = db.query(RegistrationEvent).filter(RegistrationEvent.id == event_id, RegistrationEvent.published.is_(True)).with_for_update().first()
    if not event:
        raise HTTPException(404, "Registration event not found")
    now = datetime.utcnow()
    if event.registration_deadline and event.registration_deadline <= now:
        raise HTTPException(409, "Registration for this event has closed")
    db.query(EventTicketAllocation).filter(EventTicketAllocation.event_id == event.id, EventTicketAllocation.status == "HELD", EventTicketAllocation.expires_at <= now).update({EventTicketAllocation.status: "EXPIRED"}, synchronize_session=False)
    duplicate = db.query(EventTicketAllocation.id).filter(EventTicketAllocation.event_id == event.id, or_(EventTicketAllocation.student_id == user.id, EventTicketAllocation.roll_number == payload.roll_number.strip().upper()), EventTicketAllocation.status.in_(ACTIVE_TICKET_STATES)).first()
    if duplicate:
        raise HTTPException(409, "You already have a registration for this event")
    occupied = db.query(func.count(EventTicketAllocation.id)).filter(EventTicketAllocation.event_id == event.id, or_(EventTicketAllocation.status == "CONFIRMED", EventTicketAllocation.expires_at > now)).scalar()
    if occupied >= event.capacity:
        raise HTTPException(409, "This event is full")
    booking_id = str(uuid4())
    ticket = EventTicketAllocation(event_id=event.id, student_id=user.id, roll_number=payload.roll_number.strip().upper(), participant_name=payload.participant_name.strip(), department=payload.department.strip(), status="HELD", booking_id=booking_id, expires_at=now + timedelta(minutes=10))
    db.add(ticket)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "You already have a registration for this event")
    return {"booking_id": booking_id, "status": "HELD", "expires_at": ticket.expires_at, "message": "Your seat is held for ten minutes"}

@router.post("/{event_id}/confirm", dependencies=[Depends(require_role(["STUDENT"]))])
def confirm_ticket(event_id: int, payload: TicketConfirm, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ticket = db.query(EventTicketAllocation).filter(EventTicketAllocation.event_id == event_id, EventTicketAllocation.student_id == user.id, EventTicketAllocation.booking_id == payload.booking_id).with_for_update().first()
    if not ticket or ticket.status != "HELD" or ticket.expires_at <= datetime.utcnow():
        if ticket and ticket.status == "HELD": ticket.status = "EXPIRED"; db.commit()
        raise HTTPException(409, "This ticket hold is no longer valid")
    ticket.status = "CONFIRMED"; ticket.expires_at = None; db.commit()
    return {"message": "Ticket confirmed"}

@router.get("/{event_id}/applicants", dependencies=[Depends(require_role(["FACULTY", "ADMIN"]))])
def event_applicants(event_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    event = db.query(RegistrationEvent).filter(RegistrationEvent.id == event_id).first()
    if not event or event.faculty_id != user.id:
        raise HTTPException(403, "Only the event owner can view applicants")
    now = datetime.utcnow()
    applicants = db.query(EventTicketAllocation).filter(EventTicketAllocation.event_id == event.id, or_(EventTicketAllocation.status == "CONFIRMED", EventTicketAllocation.expires_at > now)).order_by(EventTicketAllocation.created_at).all()
    return {"event": serialize_event(db, event), "applicants": applicants}
