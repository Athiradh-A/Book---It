from typing import Optional
from app.models.models import StudentProfile, Event, EligibilityRule
from app.schemas.schemas import EligibilityCheckResult

def evaluate_student_eligibility(profile: Optional[StudentProfile], rule: Optional[EligibilityRule]) -> EligibilityCheckResult:
    if not profile or profile.verification_status != "VERIFIED":
        return EligibilityCheckResult(
            is_eligible=False,
            reason="Student academic profile is missing or unverified. Please contact the Academic Registry to update your profile.",
            missing_profile=True
        )

    if not rule or rule.is_open_to_all:
        return EligibilityCheckResult(
            is_eligible=True,
            reason="This event is open to all students.",
            missing_profile=False
        )

    failed_reasons = []
    
    # 1. Programme Check (OR logic within list)
    allowed_progs = rule.allowed_programmes
    if allowed_progs and profile.programme not in allowed_progs:
        failed_reasons.append(f"degree/programme ({profile.programme} vs allowed: {', '.join(allowed_progs)})")

    # 2. Department Check (OR logic within list)
    allowed_depts = rule.allowed_departments
    if allowed_depts and profile.department not in allowed_depts:
        failed_reasons.append(f"department ({profile.department} vs allowed: {', '.join(allowed_depts)})")

    # 3. Academic Year Check (OR logic within list)
    allowed_years = rule.allowed_academic_years
    if allowed_years and profile.current_academic_year not in allowed_years:
        years_str = ", ".join([f"Year {y}" for y in allowed_years])
        failed_reasons.append(f"academic year (Your profile: Year {profile.current_academic_year} vs allowed: {years_str})")

    # 4. Graduating Batch Check (OR logic within list)
    allowed_batches = rule.allowed_batches
    if allowed_batches and profile.graduating_batch not in allowed_batches:
        batches_str = ", ".join([str(b) for b in allowed_batches])
        failed_reasons.append(f"graduating batch (Your batch: {profile.graduating_batch} vs allowed: {batches_str})")

    if failed_reasons:
        requirement_desc = []
        if allowed_progs: requirement_desc.append(" ".join(allowed_progs))
        if allowed_depts: requirement_desc.append(" ".join(allowed_depts))
        if allowed_years: requirement_desc.append(", ".join([f"Year {y}" for y in allowed_years]))
        if allowed_batches: requirement_desc.append(f"Batch {', '.join([str(b) for b in allowed_batches])}")

        req_text = " ".join(requirement_desc)
        detail_reason = f"This event is restricted to {req_text} students. Your current academic profile does not meet these requirements: {'; '.join(failed_reasons)}."
        return EligibilityCheckResult(
            is_eligible=False,
            reason=detail_reason,
            missing_profile=False
        )

    return EligibilityCheckResult(
        is_eligible=True,
        reason="Your academic profile meets all eligibility requirements for this event.",
        missing_profile=False
    )
