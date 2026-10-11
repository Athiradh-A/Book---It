from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models import User, EventRequest, ApprovalLog, Notification
from backend.app.schemas import EventRequestCreate

# --- Helper: Notifications with Email Failure Resilience ---
def send_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    related_event_id: Optional[int] = None,
    simulate_email_failure: bool = False
) -> Notification:
    email_status = "SENT"
    if simulate_email_failure:
        email_status = "FAILED_FALLBACK_PORTAL_PRESERVED"
    
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_event_id=related_event_id,
        is_read=False,
        email_status=email_status,
        created_at=datetime.now(timezone.utc)
    )
    db.add(notif)
    return notif


# --- Event Request CRUD & Workflow ---
def create_event_request(db: Session, req: EventRequestCreate) -> EventRequest:
    event_req = EventRequest(
        title=req.title,
        purpose=req.purpose,
        venue=req.venue,
        event_date=req.event_date,
        start_time=req.start_time,
        end_time=req.end_time,
        expected_attendance=req.expected_attendance,
        budget=req.budget,
        student_coordinator_id=req.student_coordinator_id,
        faculty_coordinator_id=req.faculty_coordinator_id,
        supporting_docs=req.supporting_docs,
        status="SUBMITTED",
        current_stage="FACULTY"
    )
    db.add(event_req)
    db.commit()
    db.refresh(event_req)

    student = db.get(User, req.student_coordinator_id)
    actor_name = student.full_name if student else "Student"
    
    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=req.student_coordinator_id,
        actor_name=actor_name,
        actor_role="STUDENT",
        stage="FACULTY",
        action="SUBMIT",
        comments="Submitted event request for faculty approval."
    )
    db.add(log)
    
    send_notification(
        db,
        user_id=req.faculty_coordinator_id,
        title="New Event Request For Review",
        message=f"Event '{req.title}' submitted by {actor_name} requires your review.",
        notification_type="APPROVAL_UPDATE",
        related_event_id=event_req.id
    )
    db.commit()
    return event_req


def faculty_approve_event(db: Session, event_id: int, actor_id: str, comments: Optional[str] = None) -> EventRequest:
    event_req = db.get(EventRequest, event_id)
    if not event_req:
        raise HTTPException(status_code=404, detail="Event request not found")
    if event_req.current_stage != "FACULTY":
        raise HTTPException(status_code=400, detail="Event is not in Faculty review stage")

    actor = db.get(User, actor_id)
    if not actor or actor.role != "FACULTY_COORDINATOR":
        raise HTTPException(status_code=403, detail="Unauthorized role for Faculty review")

    event_req.status = "FACULTY_APPROVED"
    event_req.current_stage = "STUDENT_WELFARE"

    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role,
        stage="FACULTY",
        action="FACULTY_APPROVE",
        comments=comments or "Faculty Coordinator authenticated and approved proposal."
    )
    db.add(log)

    welfare_users = db.query(User).filter(User.role == "STUDENT_WELFARE").all()
    for w in welfare_users:
        send_notification(
            db,
            user_id=w.id,
            title="Event Request Pending Student Welfare Review",
            message=f"Event '{event_req.title}' has been approved by Faculty Coordinator and awaits Welfare review.",
            notification_type="APPROVAL_UPDATE",
            related_event_id=event_req.id
        )
    db.commit()
    db.refresh(event_req)
    return event_req


def welfare_approve_event(db: Session, event_id: int, actor_id: str, comments: Optional[str] = None) -> EventRequest:
    event_req = db.get(EventRequest, event_id)
    if not event_req:
        raise HTTPException(status_code=404, detail="Event request not found")
    if event_req.current_stage != "STUDENT_WELFARE":
        raise HTTPException(status_code=400, detail="Event is not in Student Welfare review stage")

    actor = db.get(User, actor_id)
    if not actor or actor.role != "STUDENT_WELFARE":
        raise HTTPException(status_code=403, detail="Unauthorized role for Student Welfare review")

    event_req.status = "STUDENT_WELFARE_APPROVED"
    event_req.current_stage = "CAMPUS_DIRECTOR"

    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role,
        stage="STUDENT_WELFARE",
        action="WELFARE_APPROVE",
        comments=comments or "Student Welfare approved proposal. Forwarded to Campus Director."
    )
    db.add(log)

    cd_users = db.query(User).filter(User.role.in_(["CAMPUS_DIRECTOR", "DIRECTOR_OFFICE"])).all()
    for u in cd_users:
        send_notification(
            db,
            user_id=u.id,
            title="Pending Request: Campus Director Review",
            message=f"Event '{event_req.title}' is pending Campus Director review (Direct Approve/Reject or Request a Meeting).",
            notification_type="APPROVAL_UPDATE",
            related_event_id=event_req.id
        )
    db.commit()
    db.refresh(event_req)
    return event_req


# --- Campus Director Actions ---

# Direct Approve / Reject / Return (Path A or after Meeting Request)
def director_direct_decision(db: Session, event_id: int, actor_id: str, decision: str, comments: Optional[str] = None) -> EventRequest:
    event_req = db.get(EventRequest, event_id)
    if not event_req:
        raise HTTPException(status_code=404, detail="Event request not found")
    if event_req.current_stage != "CAMPUS_DIRECTOR":
        raise HTTPException(status_code=400, detail="Event is not in Campus Director review stage")

    actor = db.get(User, actor_id)
    if not actor or actor.role not in ["CAMPUS_DIRECTOR", "DIRECTOR_OFFICE"]:
        raise HTTPException(status_code=403, detail="Unauthorized: Only Campus Director or authorized Office Staff can perform this action.")

    if decision == "APPROVE":
        event_req.status = "CAMPUS_DIRECTOR_APPROVED"
        event_req.current_stage = "EVENTS_DEPARTMENT"
        action_name = "DIRECTOR_DIRECT_APPROVE"
        log_msg = comments or "Campus Director approved event request."
        
        events_users = db.query(User).filter(User.role == "EVENTS_DEPARTMENT").all()
        for eu in events_users:
            send_notification(
                db, user_id=eu.id, title="Final Approval Required",
                message=f"Event '{event_req.title}' approved by Campus Director and awaits Events Dept finalization.",
                notification_type="APPROVAL_UPDATE", related_event_id=event_req.id
            )
    elif decision == "REJECT":
        event_req.status = "REJECTED"
        event_req.current_stage = "REJECTED"
        action_name = "DIRECTOR_DIRECT_REJECT"
        log_msg = comments or "Campus Director rejected event request."
        
        send_notification(
            db, user_id=event_req.student_coordinator_id, title="Event Request Rejected",
            message=f"Your event request '{event_req.title}' was rejected by the Campus Director.",
            notification_type="APPROVAL_UPDATE", related_event_id=event_req.id
        )
    elif decision == "RETURN_FOR_CLARIFICATION":
        event_req.status = "RETURNED_FOR_CLARIFICATION"
        action_name = "DIRECTOR_RETURN_CLARIFICATION"
        log_msg = comments or "Campus Director returned proposal for student clarification."

        send_notification(
            db, user_id=event_req.student_coordinator_id, title="Event Proposal Returned for Clarification",
            message=f"Campus Director requested clarification for '{event_req.title}'. Notes: {comments or ''}",
            notification_type="APPROVAL_UPDATE", related_event_id=event_req.id
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Choose APPROVE, REJECT, or RETURN_FOR_CLARIFICATION.")

    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role,
        stage="CAMPUS_DIRECTOR",
        action=action_name,
        comments=log_msg
    )
    db.add(log)
    db.commit()
    db.refresh(event_req)
    return event_req


# Request a Meeting Notification (Path B - Notification to Student)
def director_request_meeting(
    db: Session,
    event_id: int,
    actor_id: str,
    comments: Optional[str] = None
) -> EventRequest:
    event_req = db.get(EventRequest, event_id)
    if not event_req:
        raise HTTPException(status_code=404, detail="Event request not found")
    if event_req.current_stage != "CAMPUS_DIRECTOR":
        raise HTTPException(status_code=400, detail="Event is not in Campus Director review stage")

    actor = db.get(User, actor_id)
    if not actor or actor.role not in ["CAMPUS_DIRECTOR", "DIRECTOR_OFFICE"]:
        raise HTTPException(status_code=403, detail="Unauthorized: Only Campus Director or Director's Office can request a meeting.")

    event_req.status = "MEETING_REQUESTED"

    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role,
        stage="CAMPUS_DIRECTOR",
        action="DIRECTOR_MEETING_REQUESTED",
        comments=comments or "Campus Director requested a meeting with the student coordinator before making a decision."
    )
    db.add(log)

    send_notification(
        db,
        user_id=event_req.student_coordinator_id,
        title="Meeting Requested by Campus Director",
        message=f"Campus Director requested a meeting regarding '{event_req.title}'. Please contact the Director's Office to figure out when and how to meet.",
        notification_type="MEETING_REQUESTED",
        related_event_id=event_req.id
    )
    db.commit()
    db.refresh(event_req)
    return event_req


# --- Final Approval by Events Department ---
def events_department_approve(db: Session, event_id: int, actor_id: str, comments: Optional[str] = None) -> EventRequest:
    event_req = db.get(EventRequest, event_id)
    if not event_req:
        raise HTTPException(status_code=404, detail="Event request not found")
    if event_req.current_stage != "EVENTS_DEPARTMENT":
        raise HTTPException(status_code=400, detail="Event is not in Events Department final approval stage")

    actor = db.get(User, actor_id)
    if not actor or actor.role != "EVENTS_DEPARTMENT":
        raise HTTPException(status_code=403, detail="Unauthorized role for Events Department approval")

    event_req.status = "APPROVED"
    event_req.current_stage = "COMPLETED"

    log = ApprovalLog(
        event_request_id=event_req.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role,
        stage="EVENTS_DEPARTMENT",
        action="EVENTS_FINAL_APPROVE",
        comments=comments or "Events Department issued final approval and scheduled campus facility booking."
    )
    db.add(log)

    send_notification(
        db,
        user_id=event_req.student_coordinator_id,
        title="Event Request Fully Approved!",
        message=f"Congratulations! Event '{event_req.title}' has received final approval from all departments.",
        notification_type="APPROVAL_UPDATE",
        related_event_id=event_req.id
    )

    db.commit()
    db.refresh(event_req)
    return event_req
