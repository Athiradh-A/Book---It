from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models.models import (
    StudentProfile, Event, EligibilityRule, EventRegistration, AcademicCalendarEntry
)
from app.services.calendar_sync import sync_event_to_calendar

def seed_database(db_session: Session = None):
    init_db()
    db = db_session if db_session else SessionLocal()

    try:
        if db.query(StudentProfile).first():
            print("Student Limited Seats Booking DB already seeded.")
            return

        # 1. Create Student Profiles
        s1 = StudentProfile(
            id="CB.EN.U4CSE22001",
            user_id="student_alice",
            full_name="Alice Wang",
            email="alice.wang@amrita.edu",
            programme="B.Tech",
            department="Computer Science",
            current_academic_year=4,
            graduating_batch=2026,
            verification_status="VERIFIED"
        )
        s2 = StudentProfile(
            id="CB.EN.U4DS24015",
            user_id="student_bob",
            full_name="Bob Martinez",
            email="bob.martinez@amrita.edu",
            programme="Integrated MSc Data Science",
            department="Data Science",
            current_academic_year=2,
            graduating_batch=2028,
            verification_status="VERIFIED"
        )
        s3 = StudentProfile(
            id="CB.EN.U4ME23042",
            user_id="student_charlie",
            full_name="Charlie Vance",
            email="charlie.vance@amrita.edu",
            programme="B.Tech",
            department="Mechanical Engineering",
            current_academic_year=3,
            graduating_batch=2027,
            verification_status="VERIFIED"
        )
        s4 = StudentProfile(
            id="CB.EN.UNVERIFIED",
            user_id="student_unverified",
            full_name="Unverified User",
            email="unverified@amrita.edu",
            programme="B.Tech",
            department="Electrical",
            current_academic_year=1,
            graduating_batch=2029,
            verification_status="UNVERIFIED"
        )
        db.add_all([s1, s2, s3, s4])
        db.commit()

        today = datetime.now(timezone.utc).replace(tzinfo=None)

        # 2. Create Events with different capabilities & eligibility rules

        # Event 1: Placement Technical Interview Masterclass (Restricted to B.Tech 4th Year - Capacity 2 seats for testing FCFS!)
        e1 = Event(
            title="Placement Technical Interview Masterclass",
            description="Intensive mock interview and resume review workshop hosted by Corporate Relations.",
            organizing_department="Corporate Relations & Placement",
            event_category="Placement",
            start_datetime=today + timedelta(days=5, hours=10),
            end_datetime=today + timedelta(days=5, hours=13),
            venue="Placement Hall A, Main Building",
            faculty_contact="Dr. K. Sivaraman (Placement Director)",
            poster_url="https://amrita.edu/posters/placement_masterclass.jpg",
            publication_status="PUBLISHED",
            is_registration_required=True,
            capacity_type="LIMITED",
            total_capacity=2,
            remaining_seats=2,
            registration_open_datetime=today - timedelta(days=1),
            registration_close_datetime=today + timedelta(days=4),
            allow_cancellation=True,
            cancellation_deadline=today + timedelta(days=4)
        )
        db.add(e1)
        db.flush()

        r1 = EligibilityRule(event_id=e1.id, is_open_to_all=False)
        r1.allowed_programmes = ["B.Tech"]
        r1.allowed_academic_years = [4]
        r1.allowed_batches = [2026]
        db.add(r1)

        # Event 2: Hands-on Python for Data Science Workshop (Restricted to Data Science - Unlimited Capacity)
        e2 = Event(
            title="Hands-on Python for Data Science & AI",
            description="Deep dive into NumPy, Pandas, Scikit-Learn for Data Science students.",
            organizing_department="Department of Data Science",
            event_category="Workshop",
            start_datetime=today + timedelta(days=10, hours=14),
            end_datetime=today + timedelta(days=10, hours=17),
            venue="Lab 4, Science Block",
            faculty_contact="Prof. Meera Nair",
            poster_url="https://amrita.edu/posters/data_science_workshop.jpg",
            publication_status="PUBLISHED",
            is_registration_required=True,
            capacity_type="UNLIMITED",
            total_capacity=None,
            remaining_seats=None,
            registration_open_datetime=today - timedelta(days=2),
            registration_close_datetime=today + timedelta(days=9),
            allow_cancellation=True
        )
        db.add(e2)
        db.flush()

        r2 = EligibilityRule(event_id=e2.id, is_open_to_all=False)
        r2.allowed_departments = ["Data Science", "Computer Science"]
        db.add(r2)

        # Event 3: Open Campus Keynote: Next-Gen Sustainable Energy (Open to All - Capacity 100)
        e3 = Event(
            title="Open Keynote: Next-Gen Sustainable Energy Solutions",
            description="Distinguished lecture by visiting international fellow on green hydrogen and solar grid integration.",
            organizing_department="School of Engineering",
            event_category="Seminar",
            start_datetime=today + timedelta(days=15, hours=11),
            end_datetime=today + timedelta(days=15, hours=13),
            venue="Amriteshwari Hall",
            faculty_contact="Dr. Sundararajan",
            poster_url=None,
            publication_status="PUBLISHED",
            is_registration_required=True,
            capacity_type="LIMITED",
            total_capacity=100,
            remaining_seats=100,
            registration_open_datetime=today - timedelta(days=3),
            registration_close_datetime=today + timedelta(days=14),
            allow_cancellation=True
        )
        db.add(e3)
        db.flush()

        r3 = EligibilityRule(event_id=e3.id, is_open_to_all=True)
        db.add(r3)

        # Event 4: Informational Announcement: Annual Sports Meet Opening (No Registration Required)
        e4 = Event(
            title="Annual Inter-Departmental Sports Meet Opening Ceremony",
            description="Official inauguration ceremony for the campus sports championship.",
            organizing_department="Department of Physical Education",
            event_category="Cultural",
            start_datetime=today + timedelta(days=20, hours=9),
            end_datetime=today + timedelta(days=20, hours=12),
            venue="Main Sports Stadium",
            faculty_contact="Coach Rajesh",
            poster_url=None,
            publication_status="PUBLISHED",
            is_registration_required=False,
            capacity_type="NONE_INFORMATIONAL",
            total_capacity=None,
            remaining_seats=None
        )
        db.add(e4)
        db.flush()

        r4 = EligibilityRule(event_id=e4.id, is_open_to_all=True)
        db.add(r4)

        # Event 5: Draft Event (Should NOT appear in discovery)
        e5 = Event(
            title="Draft Proposal: Advanced Robotics Hackathon",
            description="Draft proposal undergoing budget check.",
            organizing_department="Robotics Club",
            event_category="Symposium",
            start_datetime=today + timedelta(days=25, hours=10),
            end_datetime=today + timedelta(days=26, hours=18),
            venue="Engineering Hall C",
            publication_status="DRAFT",
            is_registration_required=True,
            capacity_type="LIMITED",
            total_capacity=50,
            remaining_seats=50
        )
        db.add(e5)
        db.flush()

        db.commit()

        # 3. Synchronize all published events to Academic Calendar
        for evt in [e1, e2, e3, e4]:
            sync_event_to_calendar(db, evt)

        print("Database successfully seeded with realistic events and eligibility rules!")
    finally:
        if not db_session:
            db.close()

if __name__ == "__main__":
    seed_database()
