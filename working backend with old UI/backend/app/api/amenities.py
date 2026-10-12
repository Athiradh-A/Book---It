from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.models import Amenity, AmenityBooking, Notification
from app.schemas.amenities import AmenityCreate, AmenityOut, AmenityBookingCreate, AmenityBookingOut, AmenityDecision

router = APIRouter(prefix="/amenities", tags=["Amenities"])

@router.get("", response_model=List[AmenityOut])
def list_amenities(category: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Amenity)
    if category:
        query = query.filter(Amenity.category == category)
    if search:
        query = query.filter(Amenity.name.ilike(f"%{search}%"))
    return query.order_by(Amenity.category, Amenity.name).all()

@router.post("", response_model=AmenityOut, status_code=201, dependencies=[Depends(require_role(["ADMIN"]))])
def create_amenity(payload: AmenityCreate, db: Session = Depends(get_db)):
    amenity = Amenity(**payload.model_dump())
    db.add(amenity); db.commit(); db.refresh(amenity)
    return amenity

@router.post("/bookings", response_model=AmenityBookingOut, status_code=201)
def book_amenity(payload: AmenityBookingCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    amenity = db.query(Amenity).filter(Amenity.id == payload.amenity_id).with_for_update().first()
    if not amenity:
        raise HTTPException(404, "Amenity not found")
    if amenity.status != "AVAILABLE":
        raise HTTPException(409, "Amenity is unavailable or under maintenance")
    reserved = db.query(func.coalesce(func.sum(AmenityBooking.quantity), 0)).filter(
        AmenityBooking.amenity_id == amenity.id,
        AmenityBooking.status.in_(["PENDING_FACULTY_APPROVAL", "CONFIRMED"]),
        AmenityBooking.start_time < payload.end_time,
        AmenityBooking.end_time > payload.start_time,
    ).scalar()
    if reserved + payload.quantity > amenity.quantity:
        raise HTTPException(409, "Requested quantity is not available for this period")
    booking = AmenityBooking(
        requester_id=user.id,
        status="PENDING_FACULTY_APPROVAL" if amenity.requires_approval else "CONFIRMED",
        **payload.model_dump(),
    )
    db.add(booking)
    db.add(Notification(user_id=user.id, message=f"Amenity request for {amenity.name} was submitted."))
    db.commit(); db.refresh(booking)
    return booking

@router.get("/bookings/my", response_model=List[AmenityBookingOut])
def my_amenity_bookings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(AmenityBooking).filter(AmenityBooking.requester_id == user.id).order_by(AmenityBooking.created_at.desc()).all()

@router.get("/bookings/pending", response_model=List[AmenityBookingOut], dependencies=[Depends(require_role(["FACULTY", "ADMIN"]))])
def pending_amenity_bookings(db: Session = Depends(get_db)):
    return db.query(AmenityBooking).filter(AmenityBooking.status == "PENDING_FACULTY_APPROVAL").all()

@router.post("/bookings/{booking_id}/decision", response_model=AmenityBookingOut, dependencies=[Depends(require_role(["FACULTY", "ADMIN"]))])
def decide_amenity_booking(booking_id: int, payload: AmenityDecision, db: Session = Depends(get_db)):
    booking = db.query(AmenityBooking).filter(AmenityBooking.id == booking_id).with_for_update().first()
    if not booking or booking.status != "PENDING_FACULTY_APPROVAL":
        raise HTTPException(409, "Request is not awaiting faculty approval")
    decision = payload.decision.upper()
    if decision not in {"APPROVED", "REJECTED", "RETURNED"}:
        raise HTTPException(422, "Decision must be APPROVED, REJECTED, or RETURNED")
    booking.status = {"APPROVED": "CONFIRMED", "REJECTED": "REJECTED", "RETURNED": "RETURNED_FOR_CHANGES"}[decision]
    booking.decision_comment = payload.comment
    booking.decided_at = datetime.utcnow()
    db.add(Notification(user_id=booking.requester_id, message=f"Your amenity request is now {booking.status.lower().replace('_', ' ')}."))
    db.commit(); db.refresh(booking)
    return booking

@router.post("/bookings/{booking_id}/cancel", response_model=AmenityBookingOut)
def cancel_amenity_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    booking = db.query(AmenityBooking).filter(AmenityBooking.id == booking_id, AmenityBooking.requester_id == user.id).with_for_update().first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status in {"CANCELLED", "REJECTED"} or booking.start_time <= datetime.utcnow():
        raise HTTPException(409, "This booking cannot be cancelled")
    booking.status = "CANCELLED"; db.commit(); db.refresh(booking)
    return booking
