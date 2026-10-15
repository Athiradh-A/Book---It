import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_roles, require_role
from app.db.session import get_db
from app.models.models import EventRequest, EventProposalDetails, EventDocument, EventMeetingRequest, ApprovalStep, Role, UserRole

router = APIRouter(prefix="/events", tags=["Event workflow"])
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".xlsx", ".pptx"}

def _can_view(event, user, roles):
    return event.requested_by == user.id or bool(set(roles) & {"FACULTY", "WELFARE", "DIRECTOR", "EVENTS", "ADMIN"})

@router.get("/{event_id}/history")
def event_history(event_id: int, db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event request not found")
    if not _can_view(event, user, roles):
        raise HTTPException(403, "You cannot view this proposal")
    detail = db.query(EventProposalDetails).filter(EventProposalDetails.event_request_id == event_id).first()
    steps = db.query(ApprovalStep).filter(ApprovalStep.event_request_id == event_id).order_by(ApprovalStep.id).all()
    meetings = db.query(EventMeetingRequest).filter(EventMeetingRequest.event_request_id == event_id).order_by(EventMeetingRequest.created_at.desc()).all()
    documents = db.query(EventDocument).filter(EventDocument.event_request_id == event_id).order_by(EventDocument.created_at).all()
    return {
        "event_id": event.id,
        "event_name": event.event_name,
        "status": event.status.value if hasattr(event.status, "value") else str(event.status),
        "current_approval_level": event.current_approval_level,
        "proposal_details": json.loads(detail.details_json) if detail else {},
        "approval_history": [{"id": x.id, "level": x.level, "approver_id": x.approver_id, "decision": x.decision, "comment": x.comment, "decided_at": x.decided_at} for x in steps],
        "meetings": [{"id": x.id, "approval_level": x.approval_level, "reason": x.reason, "preferred_at": x.preferred_at, "status": x.status, "resolution_note": x.resolution_note, "created_at": x.created_at, "resolved_at": x.resolved_at} for x in meetings],
        "documents": [{"id": x.id, "original_name": x.original_name, "mime_type": x.mime_type, "file_size": x.file_size, "created_at": x.created_at} for x in documents],
    }

@router.post("/{event_id}/documents", status_code=201)
async def upload_event_documents(event_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event request not found")
    if not _can_view(event, user, roles) or (event.requested_by != user.id and "ADMIN" not in roles):
        raise HTTPException(403, "Only the event requester or an administrator can upload documents")
    if not files or len(files) > 10:
        raise HTTPException(422, "Upload between 1 and 10 files")
    root = Path(os.getenv("BOOKIT_UPLOAD_DIR", Path(__file__).resolve().parents[2] / "uploads" / "event_documents"))
    root.mkdir(parents=True, exist_ok=True)
    saved = []
    try:
        for upload in files:
            original = Path(upload.filename or "document").name
            ext = Path(original).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(415, f"Unsupported file type: {ext or 'unknown'}")
            payload = await upload.read(MAX_FILE_SIZE + 1)
            if len(payload) > MAX_FILE_SIZE:
                raise HTTPException(413, f"{original} exceeds the 10 MB limit")
            stored = f"{uuid.uuid4().hex}{ext}"
            (root / stored).write_bytes(payload)
            row = EventDocument(event_request_id=event.id, uploaded_by=user.id, original_name=original, stored_name=stored, mime_type=upload.content_type, file_size=len(payload))
            db.add(row)
            saved.append({"original_name": original, "file_size": len(payload)})
        db.commit()
    except Exception:
        db.rollback()
        for item in saved:
            # Database rollback is authoritative; unreferenced files are safe to clean later.
            pass
        raise
    return {"uploaded": len(saved), "documents": saved}

@router.post("/{event_id}/meeting-requests", status_code=201)
def request_meeting(event_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id, EventRequest.requested_by == user.id).first()
    if not event:
        raise HTTPException(404, "Your event request was not found")
    reason = str(payload.get("reason", "")).strip()
    if len(reason) < 5:
        raise HTTPException(422, "Provide a meeting reason of at least five characters")
    preferred = payload.get("preferred_at")
    try:
        preferred_at = datetime.fromisoformat(preferred) if preferred else None
    except (TypeError, ValueError):
        raise HTTPException(422, "preferred_at must be an ISO datetime")
    meeting = EventMeetingRequest(event_request_id=event.id, requested_by=user.id, approval_level=event.current_approval_level, reason=reason, preferred_at=preferred_at)
    db.add(meeting)
    db.add(ApprovalStep(event_request_id=event.id, level=event.current_approval_level, approver_id=user.id, decision="MEETING_REQUESTED", comment=reason))
    db.commit(); db.refresh(meeting)
    return {"id": meeting.id, "status": meeting.status, "message": "Meeting request recorded"}

@router.post("/{event_id}/meeting-requests/{meeting_id}/resolve", dependencies=[Depends(require_role(["FACULTY", "WELFARE", "DIRECTOR", "EVENTS", "ADMIN"]))])
def resolve_meeting(event_id: int, meeting_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    meeting = db.query(EventMeetingRequest).filter(EventMeetingRequest.id == meeting_id, EventMeetingRequest.event_request_id == event_id).with_for_update().first()
    if not event or not meeting:
        raise HTTPException(404, "Meeting request not found")
    if "ADMIN" not in roles:
        expected = {1: "FACULTY", 2: "WELFARE", 3: "DIRECTOR", 4: "EVENTS"}.get(meeting.approval_level)
        if expected not in roles:
            raise HTTPException(403, "Your role cannot resolve this meeting")
    status_value = str(payload.get("status", "SCHEDULED")).upper()
    if status_value not in {"SCHEDULED", "RESOLVED", "DECLINED"}:
        raise HTTPException(422, "status must be SCHEDULED, RESOLVED, or DECLINED")
    note = str(payload.get("resolution_note", "")).strip()
    if not note:
        raise HTTPException(422, "A resolution note is required")
    meeting.status = status_value
    meeting.resolution_note = note
    if status_value in {"RESOLVED", "DECLINED"}:
        meeting.resolved_at = datetime.utcnow()
    db.add(ApprovalStep(event_request_id=event.id, level=meeting.approval_level, approver_id=user.id, decision=f"MEETING_{status_value}", comment=note))
    db.commit()
    return {"id": meeting.id, "status": meeting.status, "resolution_note": meeting.resolution_note}

@router.get("/{event_id}/documents/{document_id}")
def download_event_document(event_id: int, document_id: int, db: Session = Depends(get_db), user=Depends(get_current_user), roles=Depends(get_current_user_roles)):
    event = db.query(EventRequest).filter(EventRequest.id == event_id).first()
    document = db.query(EventDocument).filter(EventDocument.id == document_id, EventDocument.event_request_id == event_id).first()
    if not event or not document:
        raise HTTPException(404, "Document not found")
    if not _can_view(event, user, roles):
        raise HTTPException(403, "You cannot access this document")
    root = Path(os.getenv("BOOKIT_UPLOAD_DIR", Path(__file__).resolve().parents[2] / "uploads" / "event_documents"))
    path = root / document.stored_name
    if not path.is_file():
        raise HTTPException(404, "The stored file is not available on this server")
    return FileResponse(path, media_type=document.mime_type or "application/octet-stream", filename=document.original_name)
