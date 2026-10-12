from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import Event, AcademicCalendarEntry

def sync_event_to_calendar(db: Session, event: Event) -> AcademicCalendarEntry:
    # Calculate calendar entry status
    now = datetime.now(timezone.utc)
    # Remove tzinfo for comparison with naive DB datetimes if needed
    now_naive = now.replace(tzinfo=None)

    status = "UPCOMING"
    if event.publication_status == "CANCELLED":
        status = "CANCELLED"
    elif event.publication_status == "COMPLETED" or (event.end_datetime and event.end_datetime < now_naive):
        status = "COMPLETED"
    elif event.publication_status != "PUBLISHED":
        # If unpublished or draft, remove entry if exists
        entry = db.query(AcademicCalendarEntry).filter(AcademicCalendarEntry.source_event_id == event.id).first()
        if entry:
            db.delete(entry)
            db.commit()
        return None
    elif event.capacity_type == "LIMITED" and event.remaining_seats is not None and event.remaining_seats <= 0:
        status = "REGISTRATION_FULL"
    elif event.is_registration_required and event.registration_open_datetime and event.registration_close_datetime:
        reg_open = event.registration_open_datetime.replace(tzinfo=None) if event.registration_open_datetime.tzinfo else event.registration_open_datetime
        reg_close = event.registration_close_datetime.replace(tzinfo=None) if event.registration_close_datetime.tzinfo else event.registration_close_datetime
        if reg_open <= now_naive <= reg_close:
            status = "REGISTRATION_OPEN"

    # Idempotent upsert by source_event_id
    entry = db.query(AcademicCalendarEntry).filter(AcademicCalendarEntry.source_event_id == event.id).first()
    if not entry:
        entry = AcademicCalendarEntry(
            source_event_id=event.id,
            title=event.title,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            venue=event.venue,
            organizing_department=event.organizing_department,
            description=event.description,
            event_category=event.event_category,
            calendar_status=status,
            last_synced_at=datetime.now(timezone.utc)
        )
        db.add(entry)
    else:
        entry.title = event.title
        entry.start_datetime = event.start_datetime
        entry.end_datetime = event.end_datetime
        entry.venue = event.venue
        entry.organizing_department = event.organizing_department
        entry.description = event.description
        entry.event_category = event.event_category
        entry.calendar_status = status
        entry.last_synced_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(entry)
    return entry
