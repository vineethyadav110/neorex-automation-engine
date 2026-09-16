"""
Data Models for Integrated Job Application System.
Compatible with Pydantic v1.10.x
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ATSPlatform(str, Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    WORKDAY = "workday"
    GENERIC = "generic"


class MatchCategory(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"       # >= 75%
    MODERATE_MATCH = "MODERATE_MATCH"   # 50% - 74%
    LOW_MATCH = "LOW_MATCH"             # < 50%


class ReviewStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    USER_EDITED = "USER_EDITED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"


class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    FILE = "file"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"


class WorkExperience(BaseModel):
    title: str
    company: str
    start_date: str
    end_date: str = "Present"
    highlights: List[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    city: str
    state: str
    postal_code: Optional[str] = "75001"
    country: str = "United States"
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    us_authorized: bool = True
    requires_sponsorship: bool = False
    skills: List[str] = Field(default_factory=list)
    years_experience: float = 0.0
    experiences: List[WorkExperience] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    default_answers: Dict[str, str] = Field(default_factory=dict)
    resume_path: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class JobPosting(BaseModel):
    id: str
    title: str
    company: str
    platform: ATSPlatform = ATSPlatform.GENERIC
    url: str
    raw_text: str
    location: Optional[str] = None
    remote_policy: Optional[str] = None  # Remote, Hybrid, On-site
    extracted_required_skills: List[str] = Field(default_factory=list)
    extracted_preferred_skills: List[str] = Field(default_factory=list)
    extracted_min_years_exp: float = 0.0
    sponsorship_policy: Optional[str] = None


class EvaluationReport(BaseModel):
    job_id: str
    job_title: str
    company: str
    overall_score: int  # 0 to 100
    match_category: MatchCategory
    matched_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    experience_fit_summary: str
    eligibility_warnings: List[str] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)
    improvement_recommendations: List[str] = Field(default_factory=list)
    suggested_custom_cover_letter_hook: str = ""


class FormField(BaseModel):
    field_id: str
    label: str
    selector: str
    field_type: FieldType = FieldType.TEXT
    value: Any = ""
    options: List[str] = Field(default_factory=list)
    required: bool = False
    validation_status: str = "auto_mapped"
    notes: Optional[str] = None


class ReviewPayload(BaseModel):
    application_id: str
    job: JobPosting
    evaluation: EvaluationReport
    mapped_fields: List[FormField] = Field(default_factory=list)
    custom_screening_answers: Dict[str, str] = Field(default_factory=dict)
    tailored_cover_letter: Optional[str] = None
    resume_file_to_attach: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class SubmissionResult(BaseModel):
    application_id: str
    platform: ATSPlatform
    status: str
    message: str
    confirmation_number: Optional[str] = None
    submitted_payload: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QuestionAnswerRequest(BaseModel):
    question_text: str
    field_type: str = "textarea"  # text, textarea, select, radio
    options: List[str] = Field(default_factory=list)
    company: str = ""
    role_title: str = ""
    max_chars: Optional[int] = None


class QuestionAnswerResponse(BaseModel):
    question_text: str
    answer: str
    source: str = "generated"  # cache, rules, or generated
    selected_option: Optional[str] = None
    confidence: float = 1.0


class WorkdayStepAction(BaseModel):
    step_name: str
    inputs_to_fill: List[Dict[str, str]] = Field(default_factory=list)
    dropdowns_to_select: List[Dict[str, str]] = Field(default_factory=list)
    screening_answers: List[Dict[str, str]] = Field(default_factory=list)
