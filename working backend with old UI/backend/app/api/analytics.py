from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.models import Booking, ConflictLog, Room
from typing import Dict

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/utilization")
def get_utilization(db: Session = Depends(get_db)):
    # Calculate how many bookings each room has
    util = db.query(
        Room.code, 
        func.count(Booking.id).label("booking_count")
    ).join(Booking).group_by(Room.code).all()
    
    return {room.code: count for room, count in util}

@router.get("/conflicts")
def get_conflict_stats(db: Session = Depends(get_db)):
    stats = db.query(
        ConflictLog.conflict_type, 
        func.count(ConflictLog.id)
    ).group_by(ConflictLog.conflict_type).all()
    
    return {type: count for type, count in stats}

