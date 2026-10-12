from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, init_db
from backend.app.models import (
    User, EventRequest, ApprovalLog, Notification
)

def seed_database(db_session: Session = None):
    init_db()
    db = db_session if db_session else SessionLocal()

    try:
        if db.query(User).first():
            print("Database already seeded.")
            return

        # 1. Create Users
        users = [
            User(id="student_alice", username="alice", full_name="Alice Wang", email="alice.wang@campus.edu", role="STUDENT", department="Computer Science"),
            User(id="student_bob", username="bob", full_name="Bob Martinez", email="bob.martinez@campus.edu", role="STUDENT", department="Music & Arts"),
            User(id="faculty_smith", username="dr_smith", full_name="Dr. Robert Smith", email="dr.smith@campus.edu", role="FACULTY_COORDINATOR", department="School of Engineering"),
            User(id="welfare_dean", username="dean_miller", full_name="Dean Eleanor Miller", email="welfare.dean@campus.edu", role="STUDENT_WELFARE", department="Student Welfare Office"),
            User(id="director_johnson", username="prof_johnson", full_name="Prof. Arthur Johnson", email="director@campus.edu", role="CAMPUS_DIRECTOR", department="Office of the Campus Director"),
            User(id="office_sarah", username="sarah_ea", full_name="Sarah Connor (EA)", email="director.office@campus.edu", role="DIRECTOR_OFFICE", department="Campus Director Secretariat"),
            User(id="events_officer", username="events_admin", full_name="Marcus Vance", email="events@campus.edu", role="EVENTS_DEPARTMENT", department="Events & Facilities Office")
        ]
        db.add_all(users)
        db.commit()

        today = datetime.now(timezone.utc).date()

        # 2. Create Event Requests
        req1 = EventRequest(
            title="Annual Tech Symposium & Hackathon 2026",
            purpose="A 48-hour inter-collegiate AI & Robotics hackathon with external industry sponsors and 500+ attendees.",
            venue="Main Auditorium & Engineering Block C",
            event_date=(today + timedelta(days=20)).isoformat(),
            start_time="09:00",
            end_time="21:00",
            expected_attendance=550,
            budget=15000.0,
            student_coordinator_id="student_alice",
            faculty_coordinator_id="faculty_smith",
            supporting_docs="https://campus.edu/docs/hackathon_proposal_2026.pdf",
            status="STUDENT_WELFARE_APPROVED",
            current_stage="CAMPUS_DIRECTOR",
            created_at=datetime.now(timezone.utc) - timedelta(days=3)
        )

        req2 = EventRequest(
            title="Grand Campus Cultural Fest 2026",
            purpose="Annual music and dance showcase featuring student performances and external guest bands.",
            venue="Open Air Theatre & Sports Complex",
            event_date=(today + timedelta(days=25)).isoformat(),
            start_time="16:00",
            end_time="22:00",
            expected_attendance=1200,
            budget=25000.0,
            student_coordinator_id="student_bob",
            faculty_coordinator_id="faculty_smith",
            supporting_docs="https://campus.edu/docs/cultural_fest_proposal.pdf",
            status="STUDENT_WELFARE_APPROVED",
            current_stage="CAMPUS_DIRECTOR",
            created_at=datetime.now(timezone.utc) - timedelta(days=4)
        )

        req3 = EventRequest(
            title="Robotics Hands-on Workshop for Freshers",
            purpose="Introductory workshop on Arduino and basic motor control for 1st-year students.",
            venue="Lab 304, Electronics Wing",
            event_date=(today + timedelta(days=10)).isoformat(),
            start_time="14:00",
            end_time="17:00",
            expected_attendance=60,
            budget=1200.0,
            student_coordinator_id="student_alice",
            faculty_coordinator_id="faculty_smith",
            supporting_docs=None,
            status="SUBMITTED",
            current_stage="FACULTY",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        req4 = EventRequest(
            title="Spring Guest Speaker Series: AI Ethics",
            purpose="Keynote address by visiting research fellow on ethical AI governance.",
            venue="Seminar Hall B",
            event_date=(today + timedelta(days=30)).isoformat(),
            start_time="10:00",
            end_time="12:00",
            expected_attendance=150,
            budget=3000.0,
            student_coordinator_id="student_alice",
            faculty_coordinator_id="faculty_smith",
            supporting_docs="https://campus.edu/docs/ai_ethics_speaker.pdf",
            status="APPROVED",
            current_stage="COMPLETED",
            created_at=datetime.now(timezone.utc) - timedelta(days=10)
        )

        db.add_all([req1, req2, req3, req4])
        db.commit()

        # 3. Approval Logs
        log1_1 = ApprovalLog(
            event_request_id=req1.id,
            actor_id="student_alice",
            actor_name="Alice Wang",
            actor_role="STUDENT",
            stage="FACULTY",
            action="SUBMIT",
            comments="Submitted proposal for Annual Tech Symposium.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=3)
        )
        log1_2 = ApprovalLog(
            event_request_id=req1.id,
            actor_id="faculty_smith",
            actor_name="Dr. Robert Smith",
            actor_role="FACULTY_COORDINATOR",
            stage="FACULTY",
            action="FACULTY_APPROVE",
            comments="Approved. Proposal is academically sound and well-planned.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=2)
        )
        log1_3 = ApprovalLog(
            event_request_id=req1.id,
            actor_id="welfare_dean",
            actor_name="Dean Eleanor Miller",
            actor_role="STUDENT_WELFARE",
            stage="STUDENT_WELFARE",
            action="WELFARE_APPROVE",
            comments="Approved. Safety, security, and student welfare provisions are met.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=1)
        )

        log2_1 = ApprovalLog(
            event_request_id=req2.id,
            actor_id="student_bob",
            actor_name="Bob Martinez",
            actor_role="STUDENT",
            stage="FACULTY",
            action="SUBMIT",
            comments="Submitted Cultural Fest proposal.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=4)
        )
        log2_2 = ApprovalLog(
            event_request_id=req2.id,
            actor_id="faculty_smith",
            actor_name="Dr. Robert Smith",
            actor_role="FACULTY_COORDINATOR",
            stage="FACULTY",
            action="FACULTY_APPROVE",
            comments="Approved budget and schedule.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=3)
        )
        log2_3 = ApprovalLog(
            event_request_id=req2.id,
            actor_id="welfare_dean",
            actor_name="Dean Eleanor Miller",
            actor_role="STUDENT_WELFARE",
            stage="STUDENT_WELFARE",
            action="WELFARE_APPROVE",
            comments="Approved with crowd control condition.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=2)
        )

        db.add_all([log1_1, log1_2, log1_3, log2_1, log2_2, log2_3])
        db.commit()

        # 4. Notifications
        notif1 = Notification(
            user_id="director_johnson",
            title="Pending Director Review: Annual Tech Symposium",
            message="Event 'Annual Tech Symposium & Hackathon 2026' has passed Student Welfare review and is awaiting your decision.",
            notification_type="APPROVAL_UPDATE",
            related_event_id=req1.id,
            is_read=False,
            email_status="SENT",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        notif2 = Notification(
            user_id="office_sarah",
            title="Pending Director Review: Annual Tech Symposium",
            message="Event 'Annual Tech Symposium & Hackathon 2026' is ready for Director review or appointment scheduling.",
            notification_type="APPROVAL_UPDATE",
            related_event_id=req1.id,
            is_read=False,
            email_status="SENT",
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add_all([notif1, notif2])
        db.commit()
    finally:
        if not db_session:
            db.close()

if __name__ == "__main__":
    seed_database()
