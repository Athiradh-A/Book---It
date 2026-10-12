import pytest
import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import StudentProfile, Event, EligibilityRule, EventRegistration, AcademicCalendarEntry
from app.services.eligibility import evaluate_student_eligibility
from app.services.calendar_sync import sync_event_to_calendar

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

import asyncio
import httpx

class CustomTestClient:
    def __init__(self, app):
        self.app = app
        self.transport = httpx.ASGITransport(app=app)
        self.base_url = "http://testserver"

    def request(self, method, url, **kwargs):
        async def _req():
            async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as c:
                return await c.request(method, url, **kwargs)
        return asyncio.run(_req())

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

app.dependency_overrides[get_db] = override_get_db
client = CustomTestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test student profiles matching models.py
    s1 = StudentProfile(
        id="STD-TEST-1",
        user_id="user_alice",
        full_name="Alice BTech",
        email="alice@cb.amrita.edu",
        programme="B.Tech",
        department="Computer Science",
        current_academic_year=4,
        graduating_batch=2025,
        verification_status="VERIFIED"
    )
    s2 = StudentProfile(
        id="STD-TEST-2",
        user_id="user_bob",
        full_name="Bob MSc",
        email="bob@cb.amrita.edu",
        programme="Integrated MSc Data Science",
        department="Data Science",
        current_academic_year=2,
        graduating_batch=2027,
        verification_status="VERIFIED"
    )
    s3 = StudentProfile(
        id="STD-TEST-3",
        user_id="user_charlie",
        full_name="Charlie Incomplete",
        email="charlie@cb.amrita.edu",
        programme="B.Tech",
        department="", # Missing department
        current_academic_year=1,
        graduating_batch=2028,
        verification_status="UNVERIFIED"
    )
    db.add_all([s1, s2, s3])
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)

# --- 1. Published Event Discovery ---
def test_1_published_event_discovery():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    e_pub = Event(
        title="Published Keynote", description="Public event", organizing_department="CIR",
        event_category="CAMPUS_EVENT", venue="Hall A", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    e_draft = Event(
        title="Draft Meeting", description="Internal draft", organizing_department="CIR",
        event_category="WORKSHOP", venue="Hall B", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now, registration_close_datetime=now,
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="DRAFT"
    )
    db.add_all([e_pub, e_draft])
    db.commit()
    db.close()

    res = client.get("/api/events?student_id=STD-TEST-1")
    assert res.status_code == 200
    titles = [e["title"] for e in res.json()]
    assert "Published Keynote" in titles
    assert "Draft Meeting" not in titles

# --- 2. Event Visibility Independent of Eligibility ---
def test_2_event_visibility_independent_of_eligibility():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    e_restr = Event(
        title="Restricted Masterclass", description="Placement prep", organizing_department="CIR",
        event_category="WORKSHOP", venue="Hall C", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    db.add(e_restr)
    db.commit()

    rule = EligibilityRule(event_id=e_restr.id, is_open_to_all=False)
    rule.allowed_programmes = ["B.Tech"]
    rule.allowed_academic_years = [4]
    db.add(rule)
    db.commit()
    db.close()

    # Ineligible student (Bob - Integrated MSc, 2nd year) should still discover the event
    res = client.get("/api/events?student_id=STD-TEST-2")
    assert res.status_code == 200
    titles = [e["title"] for e in res.json()]
    assert "Restricted Masterclass" in titles

# --- 3. Open vs Restricted Eligibility Logic ---
def test_3_open_vs_restricted_eligibility():
    db = TestingSessionLocal()
    student = db.query(StudentProfile).filter_by(id="STD-TEST-2").first()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Open event
    e_open = Event(
        title="Open Event", description="Open to all", organizing_department="General",
        venue="Auditorium", start_datetime=now, end_datetime=now, publication_status="PUBLISHED"
    )
    db.add(e_open)
    db.commit()
    
    rule_open = EligibilityRule(event_id=e_open.id, is_open_to_all=True)
    db.add(rule_open)
    db.commit()

    res_open = evaluate_student_eligibility(student, rule_open)
    assert res_open.is_eligible is True
    assert "open to all" in res_open.reason.lower()

    # Restricted event
    e_restr = Event(
        title="Restricted Event", description="BTech only", organizing_department="CIR",
        venue="Lab 1", start_datetime=now, end_datetime=now, publication_status="PUBLISHED"
    )
    db.add(e_restr)
    db.commit()

    rule_restr = EligibilityRule(event_id=e_restr.id, is_open_to_all=False)
    rule_restr.allowed_programmes = ["B.Tech"]
    db.add(rule_restr)
    db.commit()

    res_restr = evaluate_student_eligibility(student, rule_restr)
    assert res_restr.is_eligible is False
    assert "programme" in res_restr.reason.lower()
    db.close()

# --- 4. Multi-Condition Eligibility (OR within rule, AND across criteria) ---
def test_4_multicondition_eligibility():
    db = TestingSessionLocal()
    alice = db.query(StudentProfile).filter_by(id="STD-TEST-1").first() # B.Tech, CS, Year 4, 2025
    bob = db.query(StudentProfile).filter_by(id="STD-TEST-2").first()   # MSc DS, DS, Year 2, 2027

    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Placement Workshop", description="Advanced prep", organizing_department="CIR",
        venue="Hall D", start_datetime=now, end_datetime=now, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()

    rule = EligibilityRule(event_id=evt.id, is_open_to_all=False)
    rule.allowed_programmes = ["B.Tech", "M.Tech"]
    rule.allowed_departments = ["Computer Science", "Data Science"]
    rule.allowed_academic_years = [4]
    db.add(rule)
    db.commit()

    # Alice matches all criteria
    res_alice = evaluate_student_eligibility(alice, rule)
    assert res_alice.is_eligible is True

    # Bob matches department (DS), but fails degree (MSc) and academic year (2)
    res_bob = evaluate_student_eligibility(bob, rule)
    assert res_bob.is_eligible is False
    db.close()

# --- 5. Clear Explanation for Ineligible Student ---
def test_5_clear_explanation_for_ineligible_student():
    db = TestingSessionLocal()
    bob = db.query(StudentProfile).filter_by(id="STD-TEST-2").first()
    now = datetime.datetime.now(datetime.timezone.utc)

    evt = Event(
        title="Senior Seminar", description="Final year only", organizing_department="CIR",
        venue="Hall E", start_datetime=now, end_datetime=now, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()

    rule = EligibilityRule(event_id=evt.id, is_open_to_all=False)
    rule.allowed_programmes = ["B.Tech"]
    rule.allowed_academic_years = [4]
    db.add(rule)
    db.commit()

    res = evaluate_student_eligibility(bob, rule)
    assert res.is_eligible is False
    assert "degree/programme" in res.reason.lower() or "academic year" in res.reason.lower()
    db.close()

# --- 6. Missing Profile Attributes ---
def test_6_missing_profile_attributes():
    db = TestingSessionLocal()
    charlie_unverified = db.query(StudentProfile).filter_by(id="STD-TEST-3").first()
    now = datetime.datetime.now(datetime.timezone.utc)

    evt = Event(
        title="Dept Workshop", description="CS only", organizing_department="CS",
        venue="Hall F", start_datetime=now, end_datetime=now, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()

    rule = EligibilityRule(event_id=evt.id, is_open_to_all=False)
    rule.allowed_departments = ["Computer Science"]
    db.add(rule)
    db.commit()

    res = evaluate_student_eligibility(charlie_unverified, rule)
    assert res.is_eligible is False
    assert res.missing_profile is True
    assert "unverified" in res.reason.lower() or "missing" in res.reason.lower()
    db.close()

# --- 7. FCFS Seat Allocation & 8. Overbooking Prevention ---
def test_7_8_fcfs_seat_allocation_and_overbooking_prevention():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Small Workshop", description="Limited 2 seats", organizing_department="CIR",
        event_category="WORKSHOP", venue="Lab 1", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=2, remaining_seats=2, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    # Student 1 books seat
    res1 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res1.status_code == 200
    assert "REG-" in res1.json()["registration_reference"]

    # Student 2 books seat
    res2 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-2", "event_id": evt_id})
    assert res2.status_code == 200

    # Student 3 tries to book full event (STD-TEST-3 is unverified, but even if verified, capacity is full)
    res3 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-3", "event_id": evt_id})
    assert res3.status_code in [400, 403]

# --- 9. Concurrent FCFS Seat Allocation ---
def test_9_concurrent_fcfs_seat_allocation():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Popular Hackathon", description="1 seat left", organizing_department="CIR",
        event_category="WORKSHOP", venue="Auditorium", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=1, remaining_seats=1, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    def try_book(std_id):
        c = CustomTestClient(app)
        return c.post("/api/registrations", json={"student_profile_id": std_id, "event_id": evt_id})

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_book, "STD-TEST-1")
        f2 = executor.submit(try_book, "STD-TEST-2")
        r1 = f1.result()
        r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 200 in statuses
    assert (400 in statuses or 409 in statuses)

# --- 10. Duplicate Registration Prevention ---
def test_10_duplicate_registration_prevention():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Unique Talk", description="One per student", organizing_department="CIR",
        event_category="SEMINAR", venue="Hall D", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    # First booking
    res1 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res1.status_code == 200

    # Second booking attempt by same student
    res2 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()

# --- 11. Registration Reference Generation ---
def test_11_registration_reference_generation():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Ref Test Event", description="Reference validation", organizing_department="CIR",
        event_category="SEMINAR", venue="Hall E", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    res = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res.status_code == 200
    ref = res.json()["registration_reference"]
    assert ref.startswith("REG-")
    assert len(ref) > 10

# --- 12. Seat Release on Cancellation & 13. Re-booking Released Seat ---
def test_12_13_seat_release_and_rebooking():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Rebook Event", description="Cancel & claim test", organizing_department="CIR",
        event_category="WORKSHOP", venue="Hall F", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=1, remaining_seats=1, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    # Student 1 books sole seat
    res1 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    reg_id = res1.json()["id"]

    # Student 2 fails to book
    res2 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-2", "event_id": evt_id})
    assert res2.status_code in [400, 409]

    # Student 1 cancels seat
    res_cancel = client.post(f"/api/registrations/{reg_id}/cancel?student_id=STD-TEST-1")
    assert res_cancel.status_code == 200

    # Student 2 now re-books freed seat successfully
    res3 = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-2", "event_id": evt_id})
    assert res3.status_code == 200

# --- 14. Registration Window Enforcement ---
def test_14_registration_window_enforcement():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    # Event opening in future
    evt_future = Event(
        title="Future Event", description="Opens tomorrow", organizing_department="CIR",
        event_category="WORKSHOP", venue="Hall G", start_datetime=now + datetime.timedelta(days=2), end_datetime=now + datetime.timedelta(days=2),
        registration_open_datetime=now + datetime.timedelta(days=1), registration_close_datetime=now + datetime.timedelta(days=2),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    db.add(evt_future)
    db.commit()
    evt_id = evt_future.id
    db.close()

    res = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res.status_code == 400
    assert "open" in res.json()["detail"].lower()

# --- 15. My Registrations Dashboard Isolation ---
def test_15_my_registrations_dashboard_isolation():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Isolation Event", description="Privacy test", organizing_department="CIR",
        event_category="WORKSHOP", venue="Hall H", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=1),
        capacity_type="LIMITED", total_capacity=10, remaining_seats=10, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()
    evt_id = evt.id
    db.close()

    # Alice books
    client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})

    # Check Alice's dashboard
    res_alice = client.get("/api/registrations/me?student_id=STD-TEST-1")
    assert len(res_alice.json()) == 1
    assert res_alice.json()[0]["student_profile_id"] == "STD-TEST-1"

    # Check Bob's dashboard
    res_bob = client.get("/api/registrations/me?student_id=STD-TEST-2")
    assert len(res_bob.json()) == 0

# --- 16, 17, 18. Academic Calendar Synchronization & Idempotency ---
def test_16_17_18_academic_calendar_sync():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = Event(
        title="Synced Symposium", description="Annual symposium", organizing_department="CIR",
        event_category="SEMINAR", venue="Auditorium B", start_datetime=now, end_datetime=now + datetime.timedelta(hours=2),
        registration_open_datetime=now, registration_close_datetime=now,
        capacity_type="LIMITED", total_capacity=50, remaining_seats=50, publication_status="PUBLISHED"
    )
    db.add(evt)
    db.commit()

    # Sync to calendar
    sync_event_to_calendar(db, evt)

    # Check entry created
    cal_entry = db.query(AcademicCalendarEntry).filter_by(source_event_id=evt.id).first()
    assert cal_entry is not None
    assert cal_entry.title == "Synced Symposium"

    # Re-sync updated event (idempotency check)
    evt.title = "Updated Synced Symposium"
    sync_event_to_calendar(db, evt)

    cal_entries = db.query(AcademicCalendarEntry).filter_by(source_event_id=evt.id).all()
    assert len(cal_entries) == 1
    assert cal_entries[0].title == "Updated Synced Symposium"
    db.close()

# --- 19. Non-Registration Announcement Types ---
def test_19_non_registration_announcement_types():
    db = TestingSessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc)
    evt_info = Event(
        title="Annual Sports Meet", description="Campus sports", organizing_department="Sports",
        event_category="SPORTS_CULTURE", venue="Main Ground", start_datetime=now, end_datetime=now + datetime.timedelta(hours=5),
        registration_open_datetime=now - datetime.timedelta(hours=1), registration_close_datetime=now + datetime.timedelta(hours=5),
        capacity_type="NONE_INFORMATIONAL", total_capacity=0, remaining_seats=0, publication_status="PUBLISHED"
    )
    db.add(evt_info)
    db.commit()
    evt_id = evt_info.id
    db.close()

    res = client.post("/api/registrations", json={"student_profile_id": "STD-TEST-1", "event_id": evt_id})
    assert res.status_code == 400
    assert "informational" in res.json()["detail"].lower() or "does not take registrations" in res.json()["detail"].lower()

# --- 20. Admin Event Management & Eligibility Configuration ---
def test_20_admin_event_management():
    now = datetime.datetime.now(datetime.timezone.utc)
    new_evt_payload = {
        "title": "Admin Created Event",
        "description": "Created via API",
        "organizing_department": "Computer Science",
        "event_category": "WORKSHOP",
        "venue": "Lab 5",
        "start_datetime": now.isoformat(),
        "end_datetime": (now + datetime.timedelta(hours=2)).isoformat(),
        "registration_open_datetime": now.isoformat(),
        "registration_close_datetime": (now + datetime.timedelta(hours=2)).isoformat(),
        "capacity_type": "LIMITED",
        "total_capacity": 30,
        "publication_status": "PUBLISHED"
    }
    res_create = client.post("/api/admin/events", json=new_evt_payload)
    assert res_create.status_code == 200
    evt_id = res_create.json()["id"]

    # Admin sets eligibility rule
    rule_payload = {
        "is_open_to_all": False,
        "allowed_programmes": ["B.Tech"],
        "allowed_academic_years": [3, 4]
    }
    res_rule = client.post(f"/api/admin/events/{evt_id}/eligibility", json=rule_payload)
    assert res_rule.status_code == 200
    assert res_rule.json()["allowed_programmes"] == ["B.Tech"]

    # Admin toggles publish status to UNPUBLISHED
    res_unpub = client.post(f"/api/admin/events/{evt_id}/publish?status=UNPUBLISHED")
    assert res_unpub.status_code == 200
    assert res_unpub.json()["publication_status"] == "UNPUBLISHED"
