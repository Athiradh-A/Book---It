import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.models import EventRequest, ApprovalLog, Notification

TEST_DB_FILE = "./test_portal.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.mark.anyio
async def test_path_a_direct_approval_without_meeting(async_client):
    """Verify Path A: Campus Director approves directly without requesting a meeting."""
    res = await async_client.get("/api/events/1")
    assert res.status_code == 200
    event = res.json()
    assert event["status"] == "STUDENT_WELFARE_APPROVED"
    assert event["current_stage"] == "CAMPUS_DIRECTOR"

    res = await async_client.post("/api/events/1/director-direct-decision", json={
        "actor_id": "director_johnson",
        "action": "APPROVE",
        "comments": "Direct approval granted after proposal review."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CAMPUS_DIRECTOR_APPROVED"
    assert data["current_stage"] == "EVENTS_DEPARTMENT"

    res = await async_client.post("/api/events/1/events-dept-approve", json={
        "actor_id": "events_officer",
        "action": "APPROVE",
        "comments": "Final facility booking confirmed."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["current_stage"] == "COMPLETED"

@pytest.mark.anyio
async def test_path_a_direct_rejection_without_meeting(async_client):
    """Verify Path A: Campus Director rejects directly without requesting a meeting."""
    res = await async_client.post("/api/events/2/director-direct-decision", json={
        "actor_id": "director_johnson",
        "action": "REJECT",
        "comments": "Facility unavailable on requested date."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["current_stage"] == "REJECTED"

@pytest.mark.anyio
async def test_path_b_meeting_notification_flow(async_client):
    """Verify Path B: Director requests meeting -> Student notified to figure out when & how -> Director explicitly approves."""
    # 1. Director requests meeting for Event #1
    res = await async_client.post("/api/events/1/director-request-meeting", json={
        "actor_id": "director_johnson",
        "comments": "Please meet to clarify security arrangements."
    })
    assert res.status_code == 200
    assert res.json()["status"] == "MEETING_REQUESTED"

    # Verify notification created for student
    notif_res = await async_client.get("/api/notifications?user_id=student_alice")
    notifs = notif_res.json()
    assert any("contact the Director's Office to figure out when and how to meet" in n["message"] for n in notifs)

    # 2. Director explicitly records decision after meeting offline
    res = await async_client.post("/api/events/1/director-direct-decision", json={
        "actor_id": "director_johnson",
        "action": "APPROVE",
        "comments": "Approved following offline meeting discussion."
    })
    assert res.status_code == 200
    assert res.json()["status"] == "CAMPUS_DIRECTOR_APPROVED"
    assert res.json()["current_stage"] == "EVENTS_DEPARTMENT"

@pytest.mark.anyio
async def test_full_approval_workflow_sequence(async_client):
    """Verify full end-to-end 5-step workflow sequence: Student -> Faculty -> Welfare -> Director -> Events Dept."""
    res = await async_client.post("/api/events", json={
        "title": "Robotics Exhibition 2026",
        "purpose": "Public showcase of student robotics projects.",
        "venue": "Campus Quadrangle",
        "event_date": "2026-11-15",
        "start_time": "10:00",
        "end_time": "16:00",
        "expected_attendance": 300,
        "budget": 5000.0,
        "student_coordinator_id": "student_alice",
        "faculty_coordinator_id": "faculty_smith"
    })
    assert res.status_code == 200
    event_id = res.json()["id"]
    assert res.json()["status"] == "SUBMITTED"

    res = await async_client.post(f"/api/events/{event_id}/faculty-approve", json={
        "actor_id": "faculty_smith", "action": "APPROVE"
    })
    assert res.json()["status"] == "FACULTY_APPROVED"

    res = await async_client.post(f"/api/events/{event_id}/welfare-approve", json={
        "actor_id": "welfare_dean", "action": "APPROVE"
    })
    assert res.json()["status"] == "STUDENT_WELFARE_APPROVED"

    res = await async_client.post(f"/api/events/{event_id}/director-direct-decision", json={
        "actor_id": "director_johnson", "action": "APPROVE"
    })
    assert res.json()["status"] == "CAMPUS_DIRECTOR_APPROVED"

    res = await async_client.post(f"/api/events/{event_id}/events-dept-approve", json={
        "actor_id": "events_officer", "action": "APPROVE"
    })
    assert res.json()["status"] == "APPROVED"
    assert res.json()["current_stage"] == "COMPLETED"
