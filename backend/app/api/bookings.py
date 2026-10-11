from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.db.session import get_db
from app.schemas.bookings import AvailabilityRequest, AvailabilityResponse, HoldRequest, HoldResponse, ConfirmRequest
from app.services.availability_service import AvailabilityService
from app.models.models import BookingHold, Booking, BookingStatus, Room, Timetable
# Removed User import from here to prevent circular dependency crashes during startup

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.get("/slots/{room_id}")
def get_room_slots(
    room_id: int, 
    date: str, 
    db: Session = Depends(get_db)
):
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
        Booking.status == BookingStatus.CONFIRMED,
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
        
        # Logic: A slot is occupied if it exists in official_classes, existing_bookings, or holds.
        is_official_class = any(tt.start_time == start_time for tt in official_classes)
        is_booked = any((b.start_time.strftime("%H:%M") == start_time) for b in existing_bookings)
        
        is_held = db.query(BookingHold).filter(
            BookingHold.room_id == room_id,
            BookingHold.status == "ACTIVE",
            BookingHold.start_time <= req_date.replace(hour=int(start_time[:2]), minute=int(start_time[3:])),
            BookingHold.end_time >= req_date.replace(hour=int(end_time[:2]), minute=int(end_time[3:])),
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

@router.post("/classroom/hold", response_model=HoldResponse)
def hold_classroom(
    request: HoldRequest, 
    db: Session = Depends(get_db)
):
    # Fetch the admin user directly inside the function
    from app.models.models import User
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        # Self-healing: Create admin user if missing
        user = User(
            username="admin",
            email="admin@college.edu",
            hashed_password="hashed_password",
            full_name="System Admin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    try:
        start_dt = datetime.fromisoformat(request.start_time)
        end_dt = datetime.fromisoformat(request.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

    hold = BookingHold(
        room_id=request.room_id,
        user_id=user.id,
        date=start_dt, 
        start_time=start_dt,
        end_time=end_dt,
        expires_at=datetime.now() + timedelta(minutes=5),
        status="ACTIVE"
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return {"hold_id": hold.id, "expires_at": hold.expires_at, "room_id": hold.room_id}

@router.post("/classroom/confirm")
def confirm_classroom_booking(
    request: ConfirmRequest, 
    db: Session = Depends(get_db)
):
    # Fetch the admin user directly inside the function
    from app.models.models import User
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        # Self-healing: Create admin user if missing
        user = User(
            username="admin",
            email="admin@college.edu",
            hashed_password="hashed_password",
            full_name="System Admin",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    from app.models.models import Room # Local import to avoid circularity
    hold = db.query(BookingHold).filter(BookingHold.id == request.hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found or expired")
    
    if hold.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="Hold has expired")

    room = db.query(Room).filter(Room.id == hold.room_id).first()
    room_type = room.room_type if room else "CLASSROOM"

    booking = Booking(
        room_id=hold.room_id,
        requester_id=user.id,
        booking_type=room_type, 
        date=hold.date,
        start_time=hold.start_time,
        end_time=hold.end_time,
        status=BookingStatus.CONFIRMED,
        purpose=request.purpose,
        expected_attendees=request.expected_attendees
    )
    
    hold.status = "CONVERTED"
    db.add(booking)
    db.commit()
    
    return {"message": "Booking confirmed successfully", "booking_id": booking.id}

