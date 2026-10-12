from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)  # STUDENT, FACULTY_COORDINATOR, STUDENT_WELFARE, CAMPUS_DIRECTOR, DIRECTOR_OFFICE, EVENTS_DEPARTMENT
    department = Column(String, nullable=True)

class EventRequest(Base):
    __tablename__ = "event_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    purpose = Column(Text, nullable=False)
    venue = Column(String, nullable=False)
    event_date = Column(String, nullable=False)  # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)    # HH:MM
    expected_attendance = Column(Integer, nullable=False)
    budget = Column(Float, default=0.0)
    student_coordinator_id = Column(String, ForeignKey("users.id"), nullable=False)
    faculty_coordinator_id = Column(String, ForeignKey("users.id"), nullable=False)
    supporting_docs = Column(Text, nullable=True)
    
    # Workflow Status: SUBMITTED, FACULTY_APPROVED, STUDENT_WELFARE_APPROVED, MEETING_REQUESTED, CAMPUS_DIRECTOR_APPROVED, RETURNED_FOR_CLARIFICATION, APPROVED, REJECTED
    status = Column(String, nullable=False, default="SUBMITTED")
    # Current Stage: FACULTY, STUDENT_WELFARE, CAMPUS_DIRECTOR, EVENTS_DEPARTMENT, COMPLETED, REJECTED
    current_stage = Column(String, nullable=False, default="FACULTY")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    student_coordinator = relationship("User", foreign_keys=[student_coordinator_id])
    faculty_coordinator = relationship("User", foreign_keys=[faculty_coordinator_id])
    approval_logs = relationship("ApprovalLog", back_populates="event_request", cascade="all, delete-orphan")


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_request_id = Column(Integer, ForeignKey("event_requests.id"), nullable=False)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False)
    actor_name = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    action = Column(String, nullable=False)
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    event_request = relationship("EventRequest", back_populates="approval_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)
    related_event_id = Column(Integer, ForeignKey("event_requests.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    email_status = Column(String, default="SENT")  # SENT, SIMULATED_LOGGED, FAILED_FALLBACK_PORTAL_PRESERVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
