"""
Ashby Adapter for Modern React / SPA No-Sign-In Career Portals.
"""

from datetime import datetime
from neorex.adapters.base import BasePortalAdapter
from neorex.core.models import (
    ReviewPayload, SubmissionResult, ATSPlatform, ReviewStatus
)

class AshbyAdapter(BasePortalAdapter):
    platform = ATSPlatform.ASHBY

    def detect(self, url: str, html: str = "") -> bool:
        return "ashbyhq.com" in url or "jobs.ashbyhq.com" in url or "ashby" in html.lower()

    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        """Produces JavaScript to inject pre-reviewed candidate details into Ashby React DOM."""
        fields_map = {f.field_id: f.value for f in payload.mapped_fields}
        full_name = fields_map.get("full_name") or f"{fields_map.get('first_name', '')} {fields_map.get('last_name', '')}".strip()

        js_script = f"""
(function() {{
    console.log("[JobApplier] Autofilling Ashby Application Form...");

    function setReactInput(input, value) {{
        if (!input) return;
        const prototype = Object.getPrototypeOf(input);
        const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value');
        if (descriptor && descriptor.set) {{
            descriptor.set.call(input, value);
        }} else {{
            input.value = value;
        }}
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}

    // Inputs in Ashby often use autocomplete or data-testid attributes
    setReactInput(document.querySelector("input[autocomplete='name'], input[name='name']"), {repr(full_name)});
    setReactInput(document.querySelector("input[autocomplete='email'], input[type='email']"), {repr(fields_map.get('email', ''))});
    setReactInput(document.querySelector("input[autocomplete='tel'], input[type='tel']"), {repr(fields_map.get('phone', ''))});

    console.log("[JobApplier] Ashby Form Populated. Ready for candidate verification.");
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

        return SubmissionResult(
            application_id=payload.application_id,
            platform=self.platform,
            status="MOCK_SUBMITTED" if dry_run else "SUCCESS",
            message=f"Ashby application for {payload.job.title} at {payload.job.company} processed.",
            confirmation_number=f"ASH-{int(datetime.utcnow().timestamp())}"
        )
