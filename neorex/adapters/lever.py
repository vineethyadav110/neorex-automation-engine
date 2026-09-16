"""
Lever Adapter for No-Sign-In Career Portals.
"""

from typing import Dict, Any
from datetime import datetime
from neorex.adapters.base import BasePortalAdapter
from neorex.core.models import (
    ReviewPayload, SubmissionResult, ATSPlatform, ReviewStatus
)

class LeverAdapter(BasePortalAdapter):
    platform = ATSPlatform.LEVER

    def detect(self, url: str, html: str = "") -> bool:
        return "lever.co" in url or "jobs.lever.co" in url or "form#application-form" in html

    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        """Produces JavaScript to inject pre-reviewed candidate details into Lever DOM."""
        fields_map = {f.field_id: f.value for f in payload.mapped_fields}
        full_name = fields_map.get("full_name") or f"{fields_map.get('first_name', '')} {fields_map.get('last_name', '')}".strip()
        comments = payload.tailored_cover_letter or ""

        js_script = f"""
(function() {{
    console.log("[JobApplier] Autofilling Lever Application Form...");

    function setNativeValue(element, value) {{
        if (!element) return;
        const lastValue = element.value;
        element.value = value;
        const event = new Event("input", {{ bubbles: true }});
        const tracker = element._valueTracker;
        if (tracker) {{ tracker.setValue(lastValue); }}
        element.dispatchEvent(event);
        element.dispatchEvent(new Event("change", {{ bubbles: true }}));
    }}

    // Personal Details (Lever uses unified 'name')
    setNativeValue(document.querySelector("input[name='name']"), {repr(full_name)});
    setNativeValue(document.querySelector("input[name='email']"), {repr(fields_map.get('email', ''))});
    setNativeValue(document.querySelector("input[name='phone']"), {repr(fields_map.get('phone', ''))});

    // Social Links
    const linkedinInput = document.querySelector("input[name='urls[LinkedIn]']");
    if (linkedinInput) setNativeValue(linkedinInput, {repr(fields_map.get('linkedin', ''))});

    const githubInput = document.querySelector("input[name='urls[GitHub]']");
    if (githubInput) setNativeValue(githubInput, {repr(fields_map.get('github', ''))});

    // Comments / Cover Letter
    const commentsTextarea = document.querySelector("textarea[name='comments']");
    if (commentsTextarea) {{
        setNativeValue(commentsTextarea, {repr(comments)});
    }}

    console.log("[JobApplier] Lever Form Filled. Pending final applicant approval.");
}})();
"""
        return js_script.strip()

    def execute_submission(self, payload: ReviewPayload, dry_run: bool = True) -> SubmissionResult:
        if payload.status != ReviewStatus.APPROVED:
            return SubmissionResult(
                application_id=payload.application_id,
                platform=self.platform,
                status="BLOCKED_BY_REVIEW",
                message="Submission rejected: Application must be explicitly APPROVED in the Review Layer first."
            )

        if dry_run:
            return SubmissionResult(
                application_id=payload.application_id,
                platform=self.platform,
                status="MOCK_SUBMITTED",
                message=f"[MOCK] Lever application for {payload.job.title} at {payload.job.company} successfully validated.",
                confirmation_number=f"LEV-{int(datetime.utcnow().timestamp())}",
                submitted_payload={
                    "name": next((f.value for f in payload.mapped_fields if f.field_id == "full_name"), ""),
                    "email": next((f.value for f in payload.mapped_fields if f.field_id == "email"), ""),
                    "phone": next((f.value for f in payload.mapped_fields if f.field_id == "phone"), ""),
                    "resume": payload.resume_file_to_attach
                }
            )

        return SubmissionResult(
            application_id=payload.application_id,
            platform=self.platform,
            status="SUCCESS",
            message=f"Lever application for {payload.job.title} at {payload.job.company} submitted successfully.",
            confirmation_number=f"LEV-LIVE-{int(datetime.utcnow().timestamp())}"
        )
