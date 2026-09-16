"""
Review Layer Engine.
Enforces Human-in-the-Loop (HITL) review and approval before any job application
is submitted to career portals.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from neorex.core.models import (
    CandidateProfile, JobPosting, EvaluationReport, ReviewPayload,
    FormField, ReviewStatus
)
from neorex.core.evaluator import JobRoleEvaluator
from neorex.core.mapper import FormFieldMapper

class ReviewLayerException(Exception):
    """Raised when review validations fail."""
    pass

class ReviewLayer:
    """Manages creation, editing, and approval workflow for job applications."""

    @classmethod
    def prepare_review_payload(cls, profile: CandidateProfile, job: JobPosting) -> ReviewPayload:
        """Assembles evaluation, mapped fields, and generated assets into a pending review payload."""
        eval_report = JobRoleEvaluator.evaluate(profile, job)
        mapped_fields = FormFieldMapper.map_standard_fields(profile, job)
        cover_letter = FormFieldMapper.generate_cover_letter(profile, job, eval_report)

        # Standard screening answers
        screening_answers = {
            "Work Authorization": "Yes" if profile.us_authorized else "No",
            "Visa Sponsorship": "Yes" if profile.requires_sponsorship else "No",
            "Notice Period": profile.default_answers.get("notice_period", "2 weeks notice"),
            "Compensation Expectation": profile.default_answers.get("salary_expectation", "Competitive / Market Rate")
        }

        app_id = f"app_{job.id}_{int(datetime.utcnow().timestamp())}"

        return ReviewPayload(
            application_id=app_id,
            job=job,
            evaluation=eval_report,
            mapped_fields=mapped_fields,
            custom_screening_answers=screening_answers,
            tailored_cover_letter=cover_letter,
            resume_file_to_attach=profile.resume_path or "Resume.pdf",
            status=ReviewStatus.PENDING_REVIEW,
            created_at=datetime.utcnow()
        )

    @classmethod
    def update_field_value(cls, payload: ReviewPayload, field_id: str, new_value: any) -> ReviewPayload:
        """Allows user to inspect and modify any auto-mapped field before submission."""
        updated = False
        for field in payload.mapped_fields:
            if field.field_id == field_id:
                field.value = new_value
                field.validation_status = "user_edited"
                updated = True
                break
        
        if not updated and field_id in payload.custom_screening_answers:
            payload.custom_screening_answers[field_id] = str(new_value)
            updated = True

        if updated and payload.status == ReviewStatus.PENDING_REVIEW:
            payload.status = ReviewStatus.USER_EDITED

        return payload

    @classmethod
    def update_cover_letter(cls, payload: ReviewPayload, new_text: str) -> ReviewPayload:
        """Allows user to customize the generated cover letter."""
        payload.tailored_cover_letter = new_text
        payload.status = ReviewStatus.USER_EDITED
        return payload

    @classmethod
    def validate_for_approval(cls, payload: ReviewPayload) -> Tuple[bool, List[str]]:
        """Pre-submission integrity audit."""
        errors = []
        for field in payload.mapped_fields:
            if field.required and (field.value is None or str(field.value).strip() == ""):
                errors.append(f"Required field '{field.label}' ({field.field_id}) is empty.")
            
            if field.field_id == "email" and ("@" not in str(field.value) or "." not in str(field.value)):
                errors.append(f"Invalid email address: {field.value}")

        if not payload.resume_file_to_attach:
            errors.append("Missing resume attachment reference.")

        return (len(errors) == 0, errors)

    @classmethod
    def approve(cls, payload: ReviewPayload, reviewer_notes: Optional[str] = None) -> ReviewPayload:
        """Approves the application package for dispatch."""
        valid, errors = cls.validate_for_approval(payload)
        if not valid:
            raise ReviewLayerException(f"Cannot approve application due to validation issues: {'; '.join(errors)}")

        payload.status = ReviewStatus.APPROVED
        payload.reviewed_at = datetime.utcnow()
        payload.review_notes = reviewer_notes or "Approved by applicant via Review Layer."
        return payload

    @classmethod
    def reject(cls, payload: ReviewPayload, reason: str) -> ReviewPayload:
        """Rejects the application (will not be submitted)."""
        payload.status = ReviewStatus.REJECTED
        payload.reviewed_at = datetime.utcnow()
        payload.review_notes = reason
        return payload

    @classmethod
    def is_eligible_for_submission(cls, payload: ReviewPayload) -> bool:
        return payload.status == ReviewStatus.APPROVED
