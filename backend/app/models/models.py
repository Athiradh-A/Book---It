from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum

class BookingStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    PENDING_FACULTY_APPROVAL = "PENDING_FACULTY_APPROVAL"
    PENDING_WELFARE_APPROVAL = "PENDING_WELFARE_APPROVAL"
    PENDING_DIRECTOR_APPROVAL = "PENDING_DIRECTOR_APPROVAL"
    PENDING_EVENTS_APPROVAL = "PENDING_EVENTS_APPROVAL"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    MAINTENANCE = "MAINTENANCE"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # e.g., STUDENT, FACULTY, ADMIN

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

class Building(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False) # Removed unique=True to allow same codes in diff blocks
    building_id = Column(Integer, ForeignKey("buildings.id"))
    academic_block = Column(String) # New column as requested
    room_type = Column(String) # e.g., CLASSROOM, HALL, AUDITORIUM
    capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    building = relationship("Building", back_populates="rooms")

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class RoomEquipment(Base):
    __tablename__ = "room_equipment"
    room_id = Column(Integer, ForeignKey("rooms.id"), primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), primary_key=True)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    department = Column(String)

class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    faculty_id = Column(Integer, ForeignKey("faculty.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    day_of_week = Column(Integer) # 0=Mon, 6=Sun
    start_time = Column(String) # HH:MM
    end_time = Column(String)   # HH:MM
    semester = Column(String)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    status = Column(String) # ACTIVE, INACTIVE

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    requester_id = Column(Integer, ForeignKey("users.id"))
    booking_type = Column(String) # CLASSROOM, HALL
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.CONFIRMED)
    purpose = Column(Text)
    expected_attendees = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))

class BookingHold(Base):
    __tablename__ = "booking_holds"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String) # ACTIVE, EXPIRED, CONVERTED

class EventRequest(Base):
    __tablename__ = "event_requests"
    id = Column(Integer, primary_key=True, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    event_name = Column(String, nullable=False)
    event_category = Column(String)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    expected_attendees = Column(Integer)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING_FACULTY_APPROVAL)
    current_approval_level = Column(Integer, default=1)

class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    id = Column(Integer, primary_key=True, index=True)
    event_request_id = Column(Integer, ForeignKey("event_requests.id"))
    level = Column(Integer)
    approver_id = Column(Integer, ForeignKey("users.id"))
    decision = Column(String) # APPROVED, REJECTED, RETURNED
    comment = Column(Text)
    decided_at = Column(DateTime(timezone=True), server_default=func.now())

class EventProposalDetails(Base):
    __tablename__ = "event_proposal_details"
    id = Column(Integer, primary_key=True, index=True)
    event_request_id = Column(Integer, ForeignKey("event_requests.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    details_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventDocument(Base):
    __tablename__ = "event_documents"
    id = Column(Integer, primary_key=True, index=True)
    event_request_id = Column(Integer, ForeignKey("event_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False, unique=True)
    mime_type = Column(String)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventMeetingRequest(Base):
    __tablename__ = "event_meeting_requests"
    id = Column(Integer, primary_key=True, index=True)
    event_request_id = Column(Integer, ForeignKey("event_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approval_level = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    preferred_at = Column(DateTime(timezone=True))
    status = Column(String, nullable=False, default="REQUESTED")
    resolution_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

class Maintenance(Base):
    __tablename__ = "maintenance"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    reason = Column(Text)
    status = Column(String) # PLANNED, ONGOING, COMPLETED

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ConflictLog(Base):
    __tablename__ = "conflict_logs"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    conflict_type = Column(String) # TIMETABLE, BOOKING, HOLD, MAINTENANCE, CAPACITY, EQUIPMENT
    details = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    entity = Column(String)
    entity_id = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    changes = Column(Text)

class AllocationRun(Base):
    __tablename__ = "allocation_runs"
    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String) # SUCCESS, FAILED
    logs = Column(Text)

class Amenity(Base):
    __tablename__ = "amenities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    description = Column(Text)
    resource_kind = Column(String, nullable=False, default="EQUIPMENT") # SPACE or EQUIPMENT
    quantity = Column(Integer, nullable=False, default=1)
    capacity = Column(Integer)
    location = Column(String)
    requires_approval = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=False, default="AVAILABLE")

class AmenityBooking(Base):
    __tablename__ = "amenity_bookings"
    id = Column(Integer, primary_key=True, index=True)
    amenity_id = Column(Integer, ForeignKey("amenities.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    purpose = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="PENDING_FACULTY_APPROVAL")
    decision_comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True))

    amenity = relationship("Amenity")

class RegistrationEvent(Base):
    __tablename__ = "registration_events"
    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    starts_at = Column(DateTime, nullable=False)
    registration_deadline = Column(DateTime)
    capacity = Column(Integer, nullable=False)
    published = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room")

class EventTicketAllocation(Base):
    __tablename__ = "event_ticket_allocations"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", name="uq_event_student_ticket"),
        UniqueConstraint("event_id", "roll_number", name="uq_event_roll_ticket"),
    )
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("registration_events.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    roll_number = Column(String, nullable=False)
    participant_name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    status = Column(String, nullable=False, default="HELD")
    booking_id = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime)

    event = relationship("RegistrationEvent")

# Add back-relationship for Building
Building.rooms = relationship("Room", back_populates="building")

