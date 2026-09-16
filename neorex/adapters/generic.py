"""
Generic Heuristic Adapter for unauthenticated career pages.
"""

from datetime import datetime
from neorex.adapters.base import BasePortalAdapter
from neorex.core.models import (
    ReviewPayload, SubmissionResult, ATSPlatform, ReviewStatus
)

class GenericAdapter(BasePortalAdapter):
    platform = ATSPlatform.GENERIC

    def detect(self, url: str, html: str = "") -> bool:
        return True  # Catch-all

    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        fields_map = {f.field_id: f.value for f in payload.mapped_fields}
        full_name = fields_map.get("full_name") or f"{fields_map.get('first_name', '')} {fields_map.get('last_name', '')}".strip()

        js_script = f"""
(function() {{
    console.log("[JobApplier] Autofilling Generic Careers Form...");

    function fillIfFound(selector, val) {{
        const el = document.querySelector(selector);
        if (el && val) {{
            el.value = val;
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }}

    fillIfFound("input[name*='first' i], input#firstName", {repr(fields_map.get('first_name', ''))});
    fillIfFound("input[name*='last' i], input#lastName", {repr(fields_map.get('last_name', ''))});
    fillIfFound("input[name='name' i], input#name", {repr(full_name)});
    fillIfFound("input[type='email'], input[name*='email' i]", {repr(fields_map.get('email', ''))});
    fillIfFound("input[type='tel'], input[name*='phone' i]", {repr(fields_map.get('phone', ''))});
    fillIfFound("input[name*='linkedin' i]", {repr(fields_map.get('linkedin', ''))});
    fillIfFound("input[name*='github' i]", {repr(fields_map.get('github', ''))});
    fillIfFound("textarea[name*='cover' i], textarea[name*='comment' i]", {repr(payload.tailored_cover_letter or '')});

    console.log("[JobApplier] Generic Form Populated.");
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
            message=f"Generic career application for {payload.job.title} processed.",
            confirmation_number=f"GEN-{int(datetime.utcnow().timestamp())}"
        )


class WorkdayAdapter(BasePortalAdapter):
    platform = ATSPlatform.WORKDAY

    def detect(self, url: str, html: str = "") -> bool:
        return "myworkdayjobs.com" in url or "myworkday.com" in url or "data-automation-id" in html

    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        fields_map = {f.field_id: f.value for f in payload.mapped_fields}

        js_script = f"""
(async function() {{
    console.log("[Neo.Rex] Running Workday Multi-Step Autofill Assistant...");

    function setNativeValue(el, val) {{
        if (!el || !val) return;
        el.focus();
        const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const desc = Object.getOwnPropertyDescriptor(proto, 'value');
        if (desc && desc.set) {{
            desc.set.call(el, val);
        }} else {{
            el.value = val;
        }}
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.blur();
        el.style.border = "2px solid #10b981";
    }}

    const fieldConfigs = [
        {{ sel: "input[data-automation-id*='firstName'], input[data-automation-id*='legalNameSection_firstName']", val: {repr(fields_map.get('first_name', ''))} }},
        {{ sel: "input[data-automation-id*='lastName'], input[data-automation-id*='legalNameSection_lastName']", val: {repr(fields_map.get('last_name', ''))} }},
        {{ sel: "input[data-automation-id*='phone'], input[data-automation-id*='phoneNumber']", val: {repr(fields_map.get('phone', ''))} }},
        {{ sel: "input[data-automation-id*='city'], input[data-automation-id*='addressSection_city']", val: {repr(fields_map.get('location', '').split(',')[0].strip())} }},
        {{ sel: "input[data-automation-id*='postalCode'], input[data-automation-id*='addressSection_postalCode']", val: '75001' }},
        {{ sel: "input[data-automation-id*='linkedin' i], input[data-automation-id*='website']", val: {repr(fields_map.get('linkedin', ''))} }}
    ];

    let count = 0;
    for (const cfg of fieldConfigs) {{
        const el = document.querySelector(cfg.sel);
        if (el && (!el.value || el.value.trim() === "")) {{
            setNativeValue(el, cfg.val);
            count++;
        }}
    }}

    const emptyTextareas = Array.from(document.querySelectorAll("textarea[data-automation-id]")).filter(t => !t.value || t.value.trim() === "");
    for (const area of emptyTextareas) {{
        const labelEl = area.closest("[data-automation-id*='formField']")?.querySelector("label");
        const qText = labelEl ? labelEl.innerText.trim() : "Screening Question";

        try {{
            const res = await fetch("http://127.0.0.1:8000/api/screening/answer", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    question_text: qText,
                    field_type: "textarea",
                    company: {repr(payload.job.company)},
                    role_title: {repr(payload.job.title)}
                }})
            }});
            if (res.ok) {{
                const data = await res.json();
                setNativeValue(area, data.answer);
                count++;
            }}
        }} catch(e) {{}}
    }}

    alert("Workday Step Autofilled: Populated " + count + " empty boxes on this step. Please review highlighted inputs and click Save & Continue.");
}})();
"""
        return js_script.strip()

    def execute_submission(self, payload: ReviewPayload, dry_run: bool = True) -> SubmissionResult:
        return SubmissionResult(
            application_id=payload.application_id,
            platform=self.platform,
            status="SUCCESS" if not dry_run else "MOCK_SUBMITTED",
            message=f"Workday application step processed for {payload.job.title}. Option A requires final native review click.",
            confirmation_number=f"WD-{int(datetime.utcnow().timestamp())}"
        )
