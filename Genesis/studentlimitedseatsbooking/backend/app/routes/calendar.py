from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AcademicCalendarEntry
from app.schemas.schemas import AcademicCalendarEntryRead

router = APIRouter(prefix="/calendar", tags=["Academic Calendar"])

@router.get("", response_model=List[AcademicCalendarEntryRead])
def list_calendar_entries(
    start_date: Optional[str] = Query(None), # YYYY-MM-DD
    end_date: Optional[str] = Query(None),   # YYYY-MM-DD
    department: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(AcademicCalendarEntry)

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(AcademicCalendarEntry.start_datetime >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(AcademicCalendarEntry.end_datetime <= end_dt)

    if department:
        query = query.filter(AcademicCalendarEntry.organizing_department == department)

    if category:
        query = query.filter(AcademicCalendarEntry.event_category == category)

    return query.order_by(AcademicCalendarEntry.start_datetime.asc()).all()
