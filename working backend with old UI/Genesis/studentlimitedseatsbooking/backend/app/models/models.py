import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String, primary_key=True) # e.g. CB.EN.U4CSE22001
    user_id = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    programme = Column(String, nullable=False) # e.g. B.Tech, Integrated MSc Data Science
    department = Column(String, nullable=False) # e.g. Computer Science, Data Science
    current_academic_year = Column(Integer, nullable=False) # e.g. 1, 2, 3, 4
    graduating_batch = Column(Integer, nullable=False) # e.g. 2026
    verification_status = Column(String, nullable=False, default="VERIFIED") # VERIFIED, UNVERIFIED

    registrations = relationship("EventRegistration", back_populates="student_profile")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    organizing_department = Column(String, nullable=False)
    event_category = Column(String, nullable=False, default="Workshop") # Workshop, Seminar, Cultural, Placement, Symposium
    
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    venue = Column(String, nullable=False)
    faculty_contact = Column(String, nullable=True)
    poster_url = Column(String, nullable=True)
    
    # Publication Status: DRAFT, PUBLISHED, UNPUBLISHED, CANCELLED, COMPLETED
    publication_status = Column(String, nullable=False, default="DRAFT")
    
    # Registration Configuration
    is_registration_required = Column(Boolean, default=True)
    capacity_type = Column(String, nullable=False, default="LIMITED") # LIMITED, UNLIMITED, NONE_INFORMATIONAL
    total_capacity = Column(Integer, nullable=True)
    remaining_seats = Column(Integer, nullable=True)
    
    registration_open_datetime = Column(DateTime, nullable=True)
    registration_close_datetime = Column(DateTime, nullable=True)
    allow_cancellation = Column(Boolean, default=True)
    cancellation_deadline = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    eligibility_rule = relationship("EligibilityRule", back_populates="event", uselist=False, cascade="all, delete-orphan")
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")
    calendar_entry = relationship("AcademicCalendarEntry", back_populates="source_event", uselist=False, cascade="all, delete-orphan")


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), unique=True, nullable=False)
    is_open_to_all = Column(Boolean, default=True)
    
    # Serialized JSON lists for criteria
    allowed_programmes_json = Column(Text, default="[]")       # e.g. ["B.Tech", "Integrated MSc Data Science"]
    allowed_departments_json = Column(Text, default="[]")      # e.g. ["Computer Science", "Data Science"]
    allowed_academic_years_json = Column(Text, default="[]")   # e.g. [2, 4]
    allowed_batches_json = Column(Text, default="[]")          # e.g. [2026, 2027]

    event = relationship("Event", back_populates="eligibility_rule")

    @property
    def allowed_programmes(self):
        return json.loads(self.allowed_programmes_json or "[]")

    @allowed_programmes.setter
    def allowed_programmes(self, val):
        self.allowed_programmes_json = json.dumps(val or [])

    @property
    def allowed_departments(self):
        return json.loads(self.allowed_departments_json or "[]")

    @allowed_departments.setter
    def allowed_departments(self, val):
        self.allowed_departments_json = json.dumps(val or [])

    @property
    def allowed_academic_years(self):
        return json.loads(self.allowed_academic_years_json or "[]")

    @allowed_academic_years.setter
    def allowed_academic_years(self, val):
        self.allowed_academic_years_json = json.dumps(val or [])

    @property
    def allowed_batches(self):
        return json.loads(self.allowed_batches_json or "[]")

    @allowed_batches.setter
    def allowed_batches(self, val):
        self.allowed_batches_json = json.dumps(val or [])


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    student_profile_id = Column(String, ForeignKey("student_profiles.id"), nullable=False)
    registration_reference = Column(String, unique=True, nullable=False) # e.g. REG-2026-A89F12
    
    # Registration Status: CONFIRMED, CANCELLED
    registration_status = Column(String, nullable=False, default="CONFIRMED")
    registration_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cancellation_timestamp = Column(DateTime, nullable=True)

    event = relationship("Event", back_populates="registrations")
    student_profile = relationship("StudentProfile", back_populates="registrations")

    __table_args__ = (
        Index("idx_active_registration", "event_id", "student_profile_id", "registration_status"),
    )


class AcademicCalendarEntry(Base):
    __tablename__ = "academic_calendar_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_event_id = Column(Integer, ForeignKey("events.id"), unique=True, nullable=False)
    title = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    venue = Column(String, nullable=False)
    organizing_department = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    event_category = Column(String, nullable=False)
    
    # Calendar Status: UPCOMING, REGISTRATION_OPEN, REGISTRATION_FULL, CANCELLED, COMPLETED
    calendar_status = Column(String, nullable=False, default="UPCOMING")
    last_synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source_event = relationship("Event", back_populates="calendar_entry")
