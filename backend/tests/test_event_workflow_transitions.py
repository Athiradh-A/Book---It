import pytest
from app.core.event_workflow import can_resubmit, decision_transition, next_approval, require_stage_role

def test_approval_stages_advance_in_order():
    assert next_approval(1) == (2, "PENDING_WELFARE_APPROVAL")
    assert next_approval(2) == (3, "PENDING_DIRECTOR_APPROVAL")
    assert next_approval(3) == (4, "PENDING_EVENTS_APPROVAL")
    assert next_approval(4) == (None, "CONFIRMED")

def test_unauthorized_stage_decision_is_denied():
    with pytest.raises(PermissionError): require_stage_role(3, {"STUDENT", "FACULTY", "WELFARE"})

def test_correct_stage_role_can_decide():
    require_stage_role(3, {"DIRECTOR"})

def test_invalid_stage_is_rejected():
    with pytest.raises(ValueError): next_approval(5)

def test_return_moves_proposal_to_requester_without_erasing_stage():
    assert decision_transition(2, "RETURNED") == (2, "RETURNED_FOR_CHANGES")
    assert can_resubmit("RETURNED_FOR_CHANGES")
    assert not can_resubmit("REJECTED")

def test_meeting_request_does_not_advance_workflow():
    assert decision_transition(3, "MEETING_REQUESTED") == (3, "PENDING_DIRECTOR_APPROVAL")

def test_final_events_approval_confirms_publication():
    assert decision_transition(4, "APPROVED") == (4, "CONFIRMED")
