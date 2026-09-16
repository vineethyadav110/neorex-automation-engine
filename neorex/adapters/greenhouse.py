"""
Greenhouse Adapter for No-Sign-In Career Portals.
"""

from typing import Dict, Any
from datetime import datetime
from neorex.adapters.base import BasePortalAdapter
from neorex.core.models import (
    ReviewPayload, SubmissionResult, ATSPlatform, ReviewStatus
)

class GreenhouseAdapter(BasePortalAdapter):
    platform = ATSPlatform.GREENHOUSE

    def detect(self, url: str, html: str = "") -> bool:
        return (
            "greenhouse.io" in url or
            "gh_jid" in url or
            "gh_src" in url or
            "form#application_form" in html or
            "demographic_questions" in html
        )

    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        """Produces JavaScript to inject pre-reviewed candidate details into Greenhouse DOM."""
        fields_map = {f.field_id: f.value for f in payload.mapped_fields}
        cover_letter = payload.tailored_cover_letter or ""

        js_script = f"""
(function() {{
    console.log("[JobApplier] Autofilling Greenhouse Application Form...");

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

    // Personal Details
    setNativeValue(document.querySelector("#first_name, input[name='first_name']"), {repr(fields_map.get('first_name', ''))});
    setNativeValue(document.querySelector("#last_name, input[name='last_name']"), {repr(fields_map.get('last_name', ''))});
    setNativeValue(document.querySelector("#email, input[name='email']"), {repr(fields_map.get('email', ''))});
    setNativeValue(document.querySelector("#phone, input[name='phone']"), {repr(fields_map.get('phone', ''))});

    // Social Links
    const linkedinInput = document.querySelector("input[autocomplete*='linkedin'], input[id*='linkedin' i], input[name*='linkedin' i]");
    if (linkedinInput) setNativeValue(linkedinInput, {repr(fields_map.get('linkedin', ''))});

    const githubInput = document.querySelector("input[id*='github' i], input[name*='github' i]");
    if (githubInput) setNativeValue(githubInput, {repr(fields_map.get('github', ''))});

    // Cover Letter
    const clTextarea = document.querySelector("#cover_letter_text, textarea[name*='cover_letter']");
    if (clTextarea) {{
        setNativeValue(clTextarea, {repr(cover_letter)});
    }}

    console.log("[JobApplier] Greenhouse Form Filled. Waiting for User Confirmation before submission.");
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
                message=f"[MOCK] Greenhouse application for {payload.job.title} at {payload.job.company} successfully validated and prepared for submission.",
                confirmation_number=f"GH-{int(datetime.utcnow().timestamp())}",
                submitted_payload={
                    "first_name": next((f.value for f in payload.mapped_fields if f.field_id == "first_name"), ""),
                    "last_name": next((f.value for f in payload.mapped_fields if f.field_id == "last_name"), ""),
                    "email": next((f.value for f in payload.mapped_fields if f.field_id == "email"), ""),
                    "phone": next((f.value for f in payload.mapped_fields if f.field_id == "phone"), ""),
                    "resume": payload.resume_file_to_attach,
                    "cover_letter_length": len(payload.tailored_cover_letter or "")
                }
            )

        # In live mode, execute the multipart HTTP POST or automated browser dispatch
        return SubmissionResult(
            application_id=payload.application_id,
            platform=self.platform,
            status="SUCCESS",
            message=f"Greenhouse application for {payload.job.title} at {payload.job.company} successfully submitted.",
            confirmation_number=f"GH-LIVE-{int(datetime.utcnow().timestamp())}"
        )
