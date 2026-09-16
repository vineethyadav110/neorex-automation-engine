import json
import os
"""
FastAPI Server for Integrated Job Application System.
Exposes RESTful endpoints for Job Evaluation, Human-in-the-Loop Review,
Strategy Synchronization, and Portal Application Dispatch.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from neorex.core.models import (
    CandidateProfile, JobPosting, EvaluationReport, ReviewPayload,
    SubmissionResult, ReviewStatus, ATSPlatform, QuestionAnswerRequest, QuestionAnswerResponse
)
from neorex.core.evaluator import JobRoleEvaluator
from neorex.core.mapper import FormFieldMapper, JobApplicationStrategy, ScreeningEngine
from neorex.core.review_layer import ReviewLayer, ReviewLayerException
from neorex.core.storage import ApplicationTrackerDB
# strategy integrated in mapper
from neorex.adapters.registry import AdapterRegistry

app = FastAPI(
    title="Integrated Job Application Engine with Review Layer",
    version="1.1.0",
    description="Automated role evaluation, form mapping, human review gate, and strategy tracking for no-sign-in career pages."
)

# Enable CORS for browser extensions and external career portal origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = ApplicationTrackerDB()
adapter_registry = AdapterRegistry()

def load_candidate_profile() -> CandidateProfile:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profile_path = os.path.join(base_dir, "data", "profile.json")
    example_path = os.path.join(base_dir, "data", "profile.example.json")

    target = profile_path if os.path.exists(profile_path) else (example_path if os.path.exists(example_path) else None)
    if target:
        try:
            with open(target, "r") as f:
                return CandidateProfile(**json.load(f))
        except Exception as e:
            print(f"[Warning] Failed loading {target}: {e}")

    return CandidateProfile(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1 (555) 019-2834",
        city="Dallas",
        state="TX",
        country="United States",
        linkedin_url="https://www.linkedin.com/in/janedoe-demo",
        github_url="https://github.com/janedoe-demo",
        portfolio_url="https://janedoe.dev",
        current_title="Data Analyst / Analytics Engineer",
        current_company="Healthcare Analytics Corp",
        us_authorized=True,
        requires_sponsorship=False,
        skills=["sql", "python", "power bi", "azure", "snowflake", "etl", "data modeling"],
        years_experience=3.5,
        default_answers={
            "notice_period": "2 weeks notice",
            "salary_expectation": "Competitive / Open to discussing range"
        },
        resume_path="resume_sample.docx"
    )

CURRENT_PROFILE: CandidateProfile = load_candidate_profile()

ACTIVE_PAYLOADS: Dict[str, ReviewPayload] = {}


class JobEvaluationRequest(BaseModel):
    title: str
    company: str
    url: str = ""
    raw_jd_text: str


class FieldUpdateRequest(BaseModel):
    application_id: str
    field_id: str
    new_value: Any


class ApprovalRequest(BaseModel):
    application_id: str
    notes: Optional[str] = "Approved after review (Option A)."


class StrategySyncRequest(BaseModel):
    application_id: str


class SubmissionRequest(BaseModel):
    application_id: str
    dry_run: bool = True


def clean_company_name(name: str) -> str:
    """Standardizes company names from URL slugs, meta tags, and scraped text."""
    if not name or name.lower() in ("company", "target company", "boards", "jobs"):
        return "Prospective Employer"
    # Clean leading 'at', trailing 'Careers', and format slugs
    clean = name.strip()
    if clean.lower().startswith("at "):
        clean = clean[3:].strip()
    clean = clean.replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in clean.split())


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Neo.Rex ATS Co-Pilot", "version": "2.0.0"}


@app.get("/api/profile", response_model=CandidateProfile)
def get_profile():
    return CURRENT_PROFILE


@app.post("/api/profile", response_model=CandidateProfile)
def update_profile(profile: CandidateProfile):
    global CURRENT_PROFILE
    CURRENT_PROFILE = profile
    return CURRENT_PROFILE


@app.post("/api/evaluate", response_model=EvaluationReport)
def evaluate_job(req: JobEvaluationRequest):
    adapter = adapter_registry.get_adapter_for_url(req.url, req.raw_jd_text)
    company = FormFieldMapper.clean_company_name(req.company, req.raw_jd_text)
    job = JobRoleEvaluator.parse_job_description(
        raw_text=req.raw_jd_text,
        title=req.title,
        company=company,
        url=req.url
    )
    job.platform = adapter.platform
    return JobRoleEvaluator.evaluate(CURRENT_PROFILE, job)


@app.post("/api/review/prepare", response_model=ReviewPayload)
def prepare_application_review(req: JobEvaluationRequest):
    adapter = adapter_registry.get_adapter_for_url(req.url, req.raw_jd_text)
    company = FormFieldMapper.clean_company_name(req.company, req.raw_jd_text)
    job = JobRoleEvaluator.parse_job_description(
        raw_text=req.raw_jd_text,
        title=req.title,
        company=company,
        url=req.url
    )
    job.platform = adapter.platform

    payload = ReviewLayer.prepare_review_payload(CURRENT_PROFILE, job)
    ACTIVE_PAYLOADS[payload.application_id] = payload
    db.save_review_payload(payload)
    return payload


@app.post("/api/review/update_field", response_model=ReviewPayload)
def update_application_field(req: FieldUpdateRequest):
    payload = ACTIVE_PAYLOADS.get(req.application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    if req.field_id == "cover_letter":
        payload = ReviewLayer.update_cover_letter(payload, str(req.new_value))
    else:
        payload = ReviewLayer.update_field_value(payload, req.field_id, req.new_value)

    ACTIVE_PAYLOADS[payload.application_id] = payload
    db.save_review_payload(payload)
    return payload


@app.post("/api/review/approve", response_model=ReviewPayload)
def approve_application(req: ApprovalRequest):
    payload = ACTIVE_PAYLOADS.get(req.application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    try:
        payload = ReviewLayer.approve(payload, req.notes)
        ACTIVE_PAYLOADS[payload.application_id] = payload
        db.save_review_payload(payload)
        return payload
    except ReviewLayerException as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/strategy/sync")
def sync_strategy(req: StrategySyncRequest):
    """Integrates with the Job Application Strategy task to generate formatted files and sync tracking records."""
    payload = ACTIVE_PAYLOADS.get(req.application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    # 1. Generate standard formatted DOCX cover letter file
    docx_file = JobApplicationStrategy.generate_cover_letter_file(payload, CURRENT_PROFILE)

    # 2. Append/update tracking entry in the Strategy Tracker format
    tracker_record = JobApplicationStrategy.sync_to_strategy_tracker(payload, docx_file)

    return {
        "status": "success",
        "application_id": req.application_id,
        "company": payload.job.company,
        "role": payload.job.title,
        "cover_letter_file": os.path.basename(docx_file),
        "cover_letter_full_path": docx_file,
        "tracker_status": tracker_record["Status"],
        "tracker_record": tracker_record
    }


@app.post("/api/submit", response_model=SubmissionResult)
def submit_application(req: SubmissionRequest):
    payload = ACTIVE_PAYLOADS.get(req.application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    if payload.status != ReviewStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail=f"Submission blocked by Review Layer. Status is '{payload.status}'. You must approve first."
        )

    adapter = adapter_registry.get_adapter_by_platform(payload.job.platform)
    result = adapter.execute_submission(payload, dry_run=req.dry_run)
    db.record_submission(result)
    return result


@app.get("/api/autofill_script/{application_id}")
def get_autofill_script(application_id: str):
    payload = ACTIVE_PAYLOADS.get(application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    adapter = adapter_registry.get_adapter_by_platform(payload.job.platform)
    script = adapter.generate_autofill_script(payload)
    return {"application_id": application_id, "script": script}



@app.get("/api/strategy/cover_letter_file/{application_id}")
def get_cover_letter_file(application_id: str):
    """Serves the generated binary DOCX cover letter file for automated in-browser file attachment."""
    payload = ACTIVE_PAYLOADS.get(application_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Application payload not found.")

    # Generate if not already generated
    docx_file = JobApplicationStrategy.generate_cover_letter_file(payload, CURRENT_PROFILE)
    if not os.path.exists(docx_file):
        raise HTTPException(status_code=500, detail="Cover letter file could not be located.")

    filename = os.path.basename(docx_file)
    return FileResponse(
        path=docx_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )



@app.post("/api/screening/answer", response_model=QuestionAnswerResponse)
def answer_screening_question(req: QuestionAnswerRequest):
    """Answers arbitrary screening questions using deterministic rules, local QA cache, and AI synthesis."""
    return ScreeningEngine.answer_question(req, CURRENT_PROFILE)


@app.get("/api/applications")
def list_applications():
    return db.list_applications()


@app.get("/api/applications/{application_id}")
def get_application(application_id: str):
    app_data = db.get_application(application_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application record not found.")
    return app_data
