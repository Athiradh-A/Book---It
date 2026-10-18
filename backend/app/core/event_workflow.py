"""Pure event approval transition rules used by the service and tests."""
STAGE_STATUS = {1: "PENDING_FACULTY_APPROVAL", 2: "PENDING_WELFARE_APPROVAL", 3: "PENDING_DIRECTOR_APPROVAL", 4: "PENDING_EVENTS_APPROVAL"}
STAGE_ROLE = {1: "FACULTY", 2: "WELFARE", 3: "DIRECTOR", 4: "EVENTS"}


def next_approval(level: int) -> tuple[int | None, str]:
    if level not in STAGE_STATUS:
        raise ValueError("Invalid approval stage")
    if level == 4:
        return None, "CONFIRMED"
    return level + 1, STAGE_STATUS[level + 1]


def require_stage_role(level: int, assigned_roles: set[str]) -> None:
    expected = STAGE_ROLE.get(level)
    if expected is None:
        raise ValueError("Invalid approval stage")
    if expected not in assigned_roles:
        raise PermissionError(f"{expected} role is required for approval stage {level}")


def decision_transition(level: int, decision: str) -> tuple[int, str]:
    """Return next (level, status); meeting requests intentionally preserve both."""
    if level not in STAGE_STATUS:
        raise ValueError("Invalid approval stage")
    decision = decision.upper()
    if decision == "MEETING_REQUESTED":
        return level, STAGE_STATUS[level]
    if decision == "RETURNED":
        return level, "RETURNED_FOR_CHANGES"
    if decision == "REJECTED":
        return level, "REJECTED"
    if decision == "APPROVED":
        next_level, status = next_approval(level)
        return (next_level if next_level is not None else level), status
    raise ValueError("Invalid decision")


def can_resubmit(status: str) -> bool:
    return status == "RETURNED_FOR_CHANGES"
