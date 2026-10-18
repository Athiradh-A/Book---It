from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.db.session import get_db
from app.schemas.bookings import AvailabilityRequest, AvailabilityResponse, HoldRequest, HoldResponse, ConfirmRequest
from app.services.availability_service import AvailabilityService
from app.models.models import BookingHold, Booking, BookingStatus, Faculty, Room, Timetable, AuditLog, Notification, User, Role, UserRole, ApprovalStep, EventRequest
from app.api.deps import get_current_user, get_current_user_roles, require_role

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.get("/slots/{room_id}")
def get_room_slots(
    room_id: int, 
    date: str, 
    db: Session = Depends(get_db)
):
    if AvailabilityService.expire_stale_holds(db):
        db.commit()
    try:
        req_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    day_of_week = req_date.weekday()
    
    # 1. Get ONLY official occupied slots from the Timetable
    official_classes = db.query(Timetable).filter(
        Timetable.room_id == room_id,
        Timetable.day_of_week == day_of_week,
        Timetable.status == "ACTIVE",
        Timetable.effective_from <= req_date,
        Timetable.effective_to >= req_date
    ).all()
    
    # 2. Get existing user bookings
    existing_bookings = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING_FACULTY_APPROVAL]),
        Booking.date >= req_date.replace(hour=0, minute=0, second=0, microsecond=0),
        Booking.date <= req_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    ).all()

    slot_timings = {
        1: ("08:00", "08:50"),
        2: ("08:50", "09:40"),
        3: ("09:40", "10:30"),
        4: ("10:45", "11:35"),
        5: ("11:35", "12:25"),
        6: ("12:25", "13:15"),
        7: ("13:15", "14:05"),
        8: ("14:05", "14:55"),
        9: ("14:55", "15:45"),
        10: ("15:45", "16:35"),
        11: ("16:35", "17:25"),
    }

    slots = []
    for slot_num in range(1, 12):
        start_time, end_time = slot_timings[slot_num]
        slot_start = req_date.replace(hour=int(start_time[:2]), minute=int(start_time[3:]))
        slot_end = req_date.replace(hour=int(end_time[:2]), minute=int(end_time[3:]))
        
        # Logic: A slot is occupied if it exists in official_classes, existing_bookings, or holds.
        is_official_class = any(
            datetime.strptime(tt.start_time, "%H:%M").time() < slot_end.time()
            and datetime.strptime(tt.end_time, "%H:%M").time() > slot_start.time()
            for tt in official_classes
        )
        is_booked = any(b.start_time < slot_end and b.end_time > slot_start for b in existing_bookings)
        
        is_held = db.query(BookingHold).filter(
            BookingHold.room_id == room_id,
            BookingHold.status == "ACTIVE",
            BookingHold.start_time < slot_end,
            BookingHold.end_time > slot_start,
            BookingHold.expires_at > datetime.now()
        ).first() is not None
        
        status = "AVAILABLE"
        if is_official_class: status = "TIMETABLE_OCCUPIED"
        elif is_booked: status = "BOOKING_OCCUPIED"
        elif is_held: status = "HELD"
        
        # Show the slot regardless of status, so the user can see what's taken
        slots.append({
            "slot": slot_num,
            "start": start_time,
            "end": end_time,
            "status": status
        })
        
    return {"room_code": room.code, "date": date, "slots": slots}

@router.get("/availability", response_model=List[AvailabilityResponse])
def get_room_availability(
    date_str: str, 
    start_str: str, 
    end_str: str, 
    capacity: int, 
    equipment_ids: str = "", 
    room_type: str = None,
    academic_block: str = None,
    building_id: int = None,
    db: Session = Depends(get_db)
):
    if AvailabilityService.expire_stale_holds(db):
        db.commit()
    try:
        req_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Handle empty time strings by providing defaults
        s_str = start_str if start_str else "09:00"
        e_str = end_str if end_str else "10:00"
        
        req_start = datetime.strptime(f"{date_str} {s_str}", "%Y-%m-%d %H:%M")
        req_end = datetime.strptime(f"{date_str} {e_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format. Use YYYY-MM-DD and HH:MM")

    eq_ids = [int(x) for x in equipment_ids.split(",") if x]

    req = AvailabilityRequest(
        date=req_date,
        start_time=req_start,
        end_time=req_end,
        required_capacity=capacity,
        required_equipment_ids=eq_ids,
        room_type=room_type,
        academic_block=academic_block,
        building_id=building_id
    )

    return [room for room in AvailabilityService.find_available_rooms(db, req) if room.is_available]

@router.get("/faculty-directory")
def faculty_directory(db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    """Return active, explicitly assigned faculty accounts students can route requests to."""
    if "STUDENT" not in roles:
        raise HTTPException(status_code=403, detail="Only students can assign a classroom faculty approver")
    rows = (
        db.query(User.id, User.email, User.full_name)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(User.is_active.is_(True), Role.name == "FACULTY")
        .order_by(User.full_name, User.email)
        .all()
    )
    return [{"id": row.id, "email": row.email, "full_name": row.full_name} for row in rows]

@router.get("/faculty-targets")
def get_faculty_targets(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(Faculty, User)
        .join(User, Faculty.user_id == User.id)
        .filter(User.is_active == True)
        .order_by(User.full_name, User.username)
        .all()
    )
    return [
        {"id": user.id, "name": user.full_name or user.username, "email": user.email}
        for faculty, user in rows
    ]

@router.post("/classroom/hold", response_model=HoldResponse)
def hold_classroom(
    request: HoldRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    roles=Depends(get_current_user_roles),
):
    if "STUDENT" not in roles:
        raise HTTPException(status_code=403, detail="Only students can request classroom bookings")
    try:
        start_dt = datetime.fromisoformat(request.start_time)
        end_dt = datetime.fromisoformat(request.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

    if end_dt <= start_dt or start_dt < datetime.now():
        raise HTTPException(status_code=422, detail="Choose a future period with an end after the start")
    room = db.query(Room).filter(Room.id == request.room_id, Room.is_active.is_(True)).with_for_update().first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    target = (
        db.query(Faculty)
        .filter(Faculty.user_id == request.target_faculty_id)
        .first()
    )
    if not target:
        raise HTTPException(
            status_code=422,
            detail="Selected faculty member does not exist",
        )
    availability = AvailabilityService.check_room_availability(db, request.room_id, AvailabilityRequest(
        date=start_dt, start_time=start_dt, end_time=end_dt,
        required_capacity=request.expected_attendees, required_equipment_ids=[]
    ))
    if not availability.is_available:
        raise HTTPException(status_code=409, detail=availability.details or "Room is not available")
    hold = BookingHold(
        room_id=request.room_id,
        user_id=user.id,
        date=start_dt, 
        start_time=start_dt,
        end_time=end_dt,
        expires_at=datetime.now() + timedelta(minutes=5),
        target_faculty_id=request.target_faculty_id,  # NEW: preserve selected approver
        status="ACTIVE"
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return {"hold_id": hold.id, "expires_at": hold.expires_at, "room_id": hold.room_id}

@router.post("/classroom/confirm")
def confirm_classroom_booking(
    request: ConfirmRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    roles=Depends(get_current_user_roles),
):
    if "STUDENT" not in roles:
        raise HTTPException(status_code=403, detail="Only students can submit classroom requests")
    hold = db.query(BookingHold).filter(BookingHold.id == request.hold_id).with_for_update().first()
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found or expired")
    
    if hold.user_id != user.id:
        raise HTTPException(status_code=403, detail="This hold belongs to another user")
    if hold.status == "CONVERTED":
        booking = db.query(Booking).filter(
            Booking.requester_id == user.id, Booking.room_id == hold.room_id,
            Booking.start_time == hold.start_time, Booking.end_time == hold.end_time,
        ).first()
        return {"message": "Classroom request already submitted", "booking_id": booking.id if booking else None, "status": booking.status.value if booking else "UNKNOWN"}
    if hold.status != "ACTIVE" or hold.expires_at < datetime.now():
        hold.status = "EXPIRED"; db.commit()
        raise HTTPException(status_code=400, detail="Hold has expired")

    availability = AvailabilityService.check_room_availability(db, hold.room_id, AvailabilityRequest(
        date=hold.date, start_time=hold.start_time, end_time=hold.end_time,
        required_capacity=request.expected_attendees, required_equipment_ids=[]
    ), ignore_hold_id=hold.id)
    if not availability.is_available:
        raise HTTPException(status_code=409, detail=availability.details or "Room is no longer available")

    # NEW: Resolve the faculty member selected when the hold was created.
    # NEW: Resolve the approver selected when the hold was created.
    faculty = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.id == hold.target_faculty_id,
            User.is_active.is_(True),
            Role.name == "FACULTY",
        )
        .first()
    )
    if not faculty:
        raise HTTPException(
            status_code=422,
            detail="The selected faculty member is no longer active or valid",
        )

    # NEW: Reject confirmation if the submitted email differs from the hold's approver.
    if faculty.email.strip().lower() != request.assigned_faculty_email.strip().lower():
        raise HTTPException(
            status_code=422,
            detail="The selected faculty member does not match this hold",
        )

    if faculty.id == user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot assign a classroom request to yourself",
        )

    room = db.query(Room).filter(Room.id == hold.room_id).first()
    room_type = room.room_type if room else "CLASSROOM"
    if (room_type or "").upper() not in {"CLASSROOM", "CLASSROOMS"}:
        raise HTTPException(status_code=422, detail="Faculty assignment is only supported for classroom requests")

    booking = Booking(
        room_id=hold.room_id,
        requester_id=user.id,
        booking_type="CLASSROOM", 
        date=hold.date,
        start_time=hold.start_time,
        end_time=hold.end_time,
        status=BookingStatus.PENDING_FACULTY_APPROVAL,
        purpose=request.purpose,
        expected_attendees=request.expected_attendees,
        # NEW: Use the faculty selected and validated during hold creation.
        assigned_faculty_id=hold.target_faculty_id,
        target_faculty_id=hold.target_faculty_id, # NEW: retain the selected approver
    )
    
    hold.status = "CONVERTED"
    db.add(booking)
    db.flush()
    db.add(Notification(user_id=user.id, message=f"Your classroom request for {room.code if room else hold.room_id} is waiting for {faculty.full_name or faculty.email}."))
    db.commit()
    
    return {"message": "Classroom request submitted for faculty approval", "booking_id": booking.id, "status": booking.status.value}

@router.get("/pending")
def pending_classroom_requests(db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    # These are direct role assignments, not inherited feature permissions. Admin and
    # workflow offices must not receive classroom approval authority by inheritance.
    if "FACULTY" not in roles:
        raise HTTPException(status_code=403, detail="Only faculty can review classroom requests")
    rows = (
        db.query(Booking, Room, User)
        .join(Room, Booking.room_id == Room.id)
        .join(User, User.id == Booking.requester_id)
        .filter(
            Booking.booking_type == "CLASSROOM",
            Booking.status == BookingStatus.PENDING_FACULTY_APPROVAL,
            Booking.assigned_faculty_id == user.id,
        )
        .order_by(Booking.start_time)
        .all()
    )
    return [
        {
            "id": booking.id, "room_id": booking.room_id, "room_code": room.code,
            "academic_block": room.academic_block, "requester_id": booking.requester_id,
            "requester_email": requester.email, "assigned_faculty_id": booking.assigned_faculty_id,
            "start_time": booking.start_time, "end_time": booking.end_time,
            "purpose": booking.purpose, "expected_attendees": booking.expected_attendees,
            "status": booking.status.value,
        }
        for booking, room, requester in rows
    ]


@router.post("/{booking_id}/decision")
def decide_classroom_request(booking_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    if "FACULTY" not in roles:
        raise HTTPException(status_code=403, detail="Only faculty can review classroom requests")
    booking = db.query(Booking).filter(Booking.id == booking_id).with_for_update().first()
    if not booking or booking.booking_type != "CLASSROOM" or booking.status != BookingStatus.PENDING_FACULTY_APPROVAL:
        raise HTTPException(409, "Classroom request is not awaiting faculty approval")
    if booking.assigned_faculty_id is None or booking.assigned_faculty_id != user.id:
        raise HTTPException(status_code=403, detail="This classroom request is assigned to another faculty member")
    decision = str(payload.get("decision", "")).upper()
    comment = str(payload.get("comment", "")).strip()
    if decision not in {"APPROVED", "REJECTED", "RETURNED"}:
        raise HTTPException(422, "Decision must be APPROVED, REJECTED, or RETURNED")
    if decision == "APPROVED":
        req = AvailabilityRequest(date=booking.date, start_time=booking.start_time, end_time=booking.end_time, required_capacity=booking.expected_attendees or 1, required_equipment_ids=[])
        conflict = AvailabilityService.check_room_availability(db, booking.room_id, req, ignore_booking_id=booking.id)
        if not conflict.is_available:
            raise HTTPException(409, f"Cannot approve this request: {conflict.details or conflict.conflict_type}")
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = datetime.utcnow()
    elif decision == "REJECTED":
        booking.status = BookingStatus.REJECTED
    else:
        booking.status = BookingStatus.RETURNED_FOR_CHANGES
    booking.decision_comment = comment
    db.add(AuditLog(user_id=user.id, action=f"CLASSROOM_{decision}", entity="Booking", entity_id=booking.id, changes=comment))
    note = f": {comment}" if comment else ""
    db.add(Notification(user_id=booking.requester_id, message=f"Your classroom request was {decision.lower().replace('_', ' ')}{note}"))
    db.commit()
    return {"id": booking.id, "status": booking.status.value, "decision_comment": booking.decision_comment}


@router.get("/{booking_id}/history")
def booking_history(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_owner = booking.requester_id == user.id
    is_assigned_faculty = booking.assigned_faculty_id == user.id and "FACULTY" in roles
    is_admin = "ADMIN" in roles
    event_approver = False
    if booking.event_request_id:
        event_approver = db.query(ApprovalStep.id).filter(ApprovalStep.event_request_id == booking.event_request_id, ApprovalStep.approver_id == user.id).first() is not None
    if not (is_owner or is_assigned_faculty or is_admin or event_approver):
        raise HTTPException(status_code=403, detail="You cannot view this booking history")
    audit = db.query(AuditLog, User).outerjoin(User, User.id == AuditLog.user_id).filter(AuditLog.entity == "Booking", AuditLog.entity_id == booking.id).order_by(AuditLog.timestamp, AuditLog.id).all()
    event_steps = []
    if booking.event_request_id:
        event_steps = db.query(ApprovalStep, User).outerjoin(User, User.id == ApprovalStep.approver_id).filter(ApprovalStep.event_request_id == booking.event_request_id).order_by(ApprovalStep.id).all()
    history_rows = [{"id": log.id, "approver_id": log.user_id, "approver_email": actor.email if actor else None, "approver_name": actor.full_name if actor else None, "decision": log.action, "comment": log.changes, "decided_at": log.timestamp} for log, actor in audit]
    if booking.booking_type == "CLASSROOM":
        requester = db.query(User).filter(User.id == booking.requester_id).first()
        history_rows.append({"id": f"submitted-{booking.id}", "approver_id": booking.requester_id, "approver_email": requester.email if requester else None, "approver_name": requester.full_name if requester else None, "decision": "SUBMITTED", "comment": f"Assigned to faculty account {booking.assigned_faculty_id}", "decided_at": booking.created_at})
    history_rows += [{"id": step.id, "approver_id": step.approver_id, "approver_email": actor.email if actor else None, "approver_name": actor.full_name if actor else None, "decision": step.decision, "comment": step.comment, "decided_at": step.decided_at, "level": step.level} for step, actor in event_steps]
    history_rows.sort(key=lambda item: str(item.get("decided_at") or ""))
    return {
        "booking_id": booking.id, "booking_type": booking.booking_type,
        "status": booking.status.value if hasattr(booking.status, "value") else str(booking.status),
        "approval_history": history_rows,
    }


@router.get("/my")
def my_bookings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    bookings = db.query(Booking).filter(Booking.requester_id == user.id).order_by(Booking.start_time.desc()).all()
    return [{"id": b.id, "room_id": b.room_id, "booking_type": b.booking_type, "start_time": b.start_time,
            "end_time": b.end_time, "status": b.status.value, "purpose": b.purpose, "decision_comment": b.decision_comment, "assigned_faculty_id": b.assigned_faculty_id, "event_request_id": b.event_request_id} for b in bookings]

@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.requester_id == user.id).with_for_update().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in {BookingStatus.CONFIRMED, BookingStatus.PENDING_FACULTY_APPROVAL} or booking.start_time <= datetime.now():
        raise HTTPException(status_code=409, detail="This booking cannot be cancelled")
    booking.status = BookingStatus.CANCELLED; db.commit()
    return {"message": "Booking cancelled"}

