"""
Interactive CLI Harness for Job Application Engine.
Enables command-line evaluation, field review, interactive editing, and submission.
"""

import sys
import os
import json
from neorex.core.models import (
    CandidateProfile, JobPosting, ATSPlatform, ReviewStatus
)
from neorex.core.evaluator import JobRoleEvaluator
from neorex.core.review_layer import ReviewLayer
from neorex.core.storage import ApplicationTrackerDB
from neorex.adapters.registry import AdapterRegistry

def run_sample_flow():
    print("=" * 70)
    print("NEO.REX: INTEGRATED JOB APPLICATION ENGINE WITH REVIEW LAYER")
    print("=" * 70)

    # 1. Candidate Profile Setup
    profile = CandidateProfile(
        first_name="Vineeth Yadav",
        last_name="Kanneboina",
        email="vineethyadavk@gmail.com",
        phone="+1 (214) 492-3576",
        city="Dallas",
        state="TX",
        linkedin_url="https://www.linkedin.com/in/vineethyadav-ms/",
        github_url="https://github.com/vineethyadav110",
        portfolio_url="https://portfolio-vineeth-yadav.vercel.app/",
        current_title="Data Analyst / Analytics Engineer",
        current_company="Tenet Healthcare",
        us_authorized=True,
        requires_sponsorship=False,
        skills=[
            "sql", "t-sql", "python", "pandas", "fastapi", "power bi", "dax",
            "azure", "azure synapse", "azure data factory", "adls", "snowflake",
            "dimensional modeling", "etl", "elt", "data quality", "git",
            "apache airflow", "healthcare analytics", "claims data"
        ],
        years_experience=3.5,
        default_answers={
            "notice_period": "2 weeks notice",
            "salary_expectation": "Competitive / Market Rate"
        },
        resume_path="Vineeth_Kanneboina_Analytics_Engineer.docx"
    )

    # 2. Sample No-Sign-In Job Posting (Greenhouse)
    sample_jd = """
    National Trench Safety is seeking a talented Analytics Engineer to join our growing team.
    
    About the Role:
    You will design, develop, and maintain analytics workflows and data transformations that drive strategic decisions.
    
    Required Qualifications:
    - 3+ years of professional experience in data analytics, data modeling, or analytics engineering.
    - Strong proficiency with SQL, T-SQL, and Python (pandas).
    - Proven expertise building dimensional data models and ETL/ELT pipelines in Azure (Azure Data Factory, Azure Synapse).
    - Experience developing scalable business intelligence dashboards using Power BI and DAX.
    - Solid understanding of data quality, automated reconciliations, and Git version control.
    
    Preferred Qualifications:
    - Experience with Snowflake, Apache Airflow, or dbt.
    - Prior exposure to healthcare or operational logistics datasets.
    
    Work Authorization:
    Must be legally authorized to work in the United States.
    """

    job = JobRoleEvaluator.parse_job_description(
        raw_text=sample_jd,
        title="Analytics Engineer",
        company="National Trench Safety",
        url="https://boards.greenhouse.io/nationaltrenchsafety/jobs/4089201003"
    )
    job.platform = ATSPlatform.GREENHOUSE

    print(f"\n[1] Target Role: {job.title} at {job.company}")
    print(f"    Portal Platform: {job.platform.value.upper()} (No Sign-In Required)")
    print(f"    URL: {job.url}")

    # 3. Job Evaluation
    print("\n" + "-" * 70)
    print("[2] EVALUATING JOB ROLE FIT...")
    eval_report = JobRoleEvaluator.evaluate(profile, job)
    print(f"    Overall Match Score: {eval_report.overall_score}% ({eval_report.match_category.value})")
    print(f"    Tenure Alignment: {eval_report.experience_fit_summary}")
    print(f"    Matched Skills ({len(eval_report.matched_skills)}): {', '.join(eval_report.matched_skills)}")
    print(f"    Missing Required: {', '.join(eval_report.missing_required_skills) if eval_report.missing_required_skills else 'None (100% Core Requirements Matched)'}")
    print(f"    Key Strengths: {eval_report.key_strengths[0] if eval_report.key_strengths else 'N/A'}")

    # 4. Review Layer Preparation
    print("\n" + "-" * 70)
    print("[3] ENTERING HUMAN-IN-THE-LOOP (HITL) REVIEW LAYER...")
    payload = ReviewLayer.prepare_review_payload(profile, job)
    print(f"    Application ID: {payload.application_id}")
    print(f"    Current Status: {payload.status.value}")
    print(f"\n    --- Pre-Filled Form Mapping Preview ---")
    for f in payload.mapped_fields:
        print(f"    * [{f.field_id}] {f.label}: '{f.value}' (Status: {f.validation_status})")

    print(f"\n    --- Tailored Cover Letter Hook Preview ---")
    print(f"    \"{payload.evaluation.suggested_custom_cover_letter_hook}\"")

    # 5. User Edit Simulation in Review Layer
    print("\n" + "-" * 70)
    print("[4] SIMULATING USER REVIEW & REVISION...")
    payload = ReviewLayer.update_field_value(payload, "phone", "+1 (214) 555-0199")
    print(f"    Updated field 'phone' -> {payload.mapped_fields[4].value}")
    print(f"    Status updated to: {payload.status.value}")

    # Verify review gate: attempting submit before approval should fail
    registry = AdapterRegistry()
    adapter = registry.get_adapter_by_platform(payload.job.platform)
    blocked_result = adapter.execute_submission(payload)
    print(f"\n    [Security Check] Attempting dispatch before approval: {blocked_result.status}")
    print(f"    Enforcement Message: {blocked_result.message}")

    # 6. Explicit Approval
    print("\n" + "-" * 70)
    print("[5] APPLICANT APPROVES APPLICATION...")
    payload = ReviewLayer.approve(payload, reviewer_notes="Confirmed all fields and customized phone number.")
    print(f"    New Status: {payload.status.value}")
    print(f"    Reviewer Notes: {payload.review_notes}")

    # 7. Execution of Submission
    print("\n" + "-" * 70)
    print("[6] EXECUTING APPLICATION SUBMISSION VIA GREENHOUSE ADAPTER...")
    submission = adapter.execute_submission(payload, dry_run=True)
    print(f"    Submission Status: {submission.status}")
    print(f"    Confirmation Number: {submission.confirmation_number}")
    print(f"    Message: {submission.message}")

    # 8. Persistence in Database
    db = ApplicationTrackerDB()
    db.save_review_payload(payload)
    db.record_submission(submission)
    saved_record = db.get_application(payload.application_id)
    print(f"\n    Saved to SQLite DB: Status={saved_record['status']}, Match={saved_record['match_score']}%")
    print("=" * 70)

if __name__ == "__main__":
    run_sample_flow()
