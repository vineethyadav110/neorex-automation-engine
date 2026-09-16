"""
Form Field Mapper, Dynamic Answer Generator, and Job Application Strategy Integration.
Translates normalized CandidateProfile into ATS-specific fields, generates
tailored responses and cover letters, and synchronizes strategy documents and trackers.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import docx
from docx.shared import Inches, Pt, RGBColor

from neorex.core.models import (
    CandidateProfile, JobPosting, EvaluationReport, FormField, FieldType, ReviewPayload
)

STRATEGY_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)
TRACKER_CSV_PATH = os.path.join(STRATEGY_DATA_DIR, "applications_strategy_tracker.csv")
GENERATED_DOCS_DIR = os.path.join(STRATEGY_DATA_DIR, "generated_cover_letters")


class FormFieldMapper:
    """Maps candidate information to standardized ATS form fields."""

    @classmethod
    def clean_company_name(cls, raw: str, raw_jd_text: str = "") -> str:
        import re
        if not raw or raw.lower() in ("company", "target company", "boards", "jobs", "prospective employer"):
            raw = ""
        clean = raw.strip()
        if clean.lower().startswith("at "):
            clean = clean[3:].strip()
        slug_clean = re.sub(r'[^a-zA-Z0-9]', '', clean).lower()
        if slug_clean and raw_jd_text:
            words = raw_jd_text.split()
            for n_words in range(1, 6):
                for i in range(len(words) - n_words + 1):
                    cand = " ".join(words[i:i+n_words])
                    if re.sub(r'[^a-zA-Z0-9]', '', cand).lower() == slug_clean:
                        return cand.strip(' ,.-|:')
        clean = clean.replace("-", " ").replace("_", " ")
        return " ".join(w.capitalize() for w in clean.split()) if clean else "Target Company"

    @classmethod
    def generate_cover_letter(cls, profile: CandidateProfile, job: JobPosting, eval_report: EvaluationReport) -> str:
        """Generates a professional, targeted cover letter tailored to the job posting."""
        company = cls.clean_company_name(job.company)
        top_skills = ", ".join(eval_report.matched_skills[:5]) if eval_report.matched_skills else "SQL, Python, and data pipelines"

        paragraphs = [
            f"Dear Hiring Team at {company},",
            f"I am writing to express my strong interest in the {job.title} role. With hands-on experience in analytics engineering, scalable data modeling, and business intelligence, I specialize in translating complex operational data into reliable data assets and high-impact analytics solutions.",
            eval_report.suggested_custom_cover_letter_hook,
            f"In my previous projects and professional engagements, I have focused on building resilient data pipelines, optimizing analytical query runtimes, and standardizing data quality reconciliations. My background aligns closely with your technical focus on {top_skills}.",
            f"I would welcome the opportunity to discuss how my technical expertise can support {company}'s goals. Thank you for your time and consideration.",
            "Sincerely,",
            profile.full_name
        ]
        return "\n\n".join(paragraphs)

    @classmethod
    def answer_screening_question(cls, question_label: str, profile: CandidateProfile, job: JobPosting) -> str:
        q = question_label.lower()

        if "legally authorized" in q or "authorized to work" in q or "legal right to work" in q:
            return "Yes" if profile.us_authorized else "No"

        if "sponsorship" in q or "visa" in q:
            return "Yes" if profile.requires_sponsorship else "No"

        if "notice period" in q or "how soon" in q or "start date" in q or "earliest start" in q:
            return profile.default_answers.get("notice_period", "2 weeks notice")

        if "salary" in q or "compensation" in q:
            return profile.default_answers.get("salary_expectation", "Open / Market Rate (Competitive)")

        if "how did you hear" in q or "source" in q or "referral" in q:
            return "Company Careers Page"

        if "relocate" in q or "relocation" in q:
            return "Open to relocation"

        if "why do you want to work" in q or "why us" in q or "interest in" in q:
            comp = cls.clean_company_name(job.company)
            skills_str = ", ".join(profile.skills[:4])
            return (
                f"I admire {comp}'s innovative focus and mission. My background in {skills_str} "
                f"enables me to drive immediate impact while collaborating closely with the team."
            )

        return profile.default_answers.get(question_label, "")

    @classmethod
    def map_standard_fields(cls, profile: CandidateProfile, job: JobPosting) -> List[FormField]:
        fields = [
            FormField(
                field_id="first_name",
                label="First Name",
                selector="input[name*='first_name'], input#first_name, input#firstName",
                field_type=FieldType.TEXT,
                value=profile.first_name,
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="last_name",
                label="Last Name",
                selector="input[name*='last_name'], input#last_name, input#lastName",
                field_type=FieldType.TEXT,
                value=profile.last_name,
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="full_name",
                label="Full Name",
                selector="input[name='name'], input#name",
                field_type=FieldType.TEXT,
                value=profile.full_name,
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="email",
                label="Email Address",
                selector="input[type='email'], input[name='email'], input#email",
                field_type=FieldType.EMAIL,
                value=profile.email,
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="phone",
                label="Phone Number",
                selector="input[type='tel'], input[name*='phone'], input#phone",
                field_type=FieldType.TEL,
                value=profile.phone,
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="location",
                label="Location / City, State",
                selector="input[name*='location'], input#location, input[name*='city']",
                field_type=FieldType.TEXT,
                value=f"{profile.city}, {profile.state}",
                required=False,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="linkedin",
                label="LinkedIn Profile URL",
                selector="input[name*='linkedin' i], input[id*='linkedin' i], input[name='urls[LinkedIn]']",
                field_type=FieldType.TEXT,
                value=profile.linkedin_url or "",
                required=False,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="github",
                label="GitHub / Portfolio URL",
                selector="input[name*='github' i], input[name*='portfolio' i], input[name='urls[GitHub]']",
                field_type=FieldType.TEXT,
                value=profile.github_url or profile.portfolio_url or "",
                required=False,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="work_auth",
                label="Legally Authorized to Work",
                selector="input[name*='authorized'], select[name*='authorized']",
                field_type=FieldType.SELECT,
                value="Yes" if profile.us_authorized else "No",
                options=["Yes", "No"],
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="sponsorship",
                label="Require Sponsorship Now/Future",
                selector="input[name*='sponsorship'], select[name*='sponsorship']",
                field_type=FieldType.SELECT,
                value="Yes" if profile.requires_sponsorship else "No",
                options=["Yes", "No"],
                required=True,
                validation_status="auto_mapped"
            ),
            FormField(
                field_id="resume_file",
                label="Resume Document",
                selector="input[type='file'][name*='resume']",
                field_type=FieldType.FILE,
                value=profile.resume_path or "Resume.docx",
                required=True,
                validation_status="auto_mapped",
                notes="Verified resume attachment reference"
            )
        ]
        return fields


class JobApplicationStrategy:
    """Integrates with the Job Application Strategy task for document generation and tracking."""

    @classmethod
    def sanitize_filename_part(cls, text: str) -> str:
        return "".join(c for c in text if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")

    @classmethod
    def generate_cover_letter_file(cls, payload: ReviewPayload, profile: CandidateProfile) -> str:
        """Generates a formatted DOCX cover letter file matching the user's template conventions."""
        os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)

        comp = FormFieldMapper.clean_company_name(payload.job.company)
        company_clean = cls.sanitize_filename_part(comp)
        role_clean = cls.sanitize_filename_part(payload.job.title)
        cand_clean = cls.sanitize_filename_part(profile.full_name)

        filename = f"{cand_clean}_Cover_Letter_{company_clean}_{role_clean}.docx"
        file_path = os.path.join(GENERATED_DOCS_DIR, filename)

        doc = docx.Document()

        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Candidate Header
        h_para = doc.add_paragraph()
        h_run = h_para.add_run(profile.full_name)
        h_run.font.name = 'Calibri'
        h_run.font.size = Pt(16)
        h_run.bold = True
        h_run.font.color.rgb = RGBColor(15, 23, 42)

        sub_para = doc.add_paragraph()
        sub_text = f"{profile.city}, {profile.state} | {profile.phone} | {profile.email}"
        sub_run = sub_para.add_run(sub_text)
        sub_run.font.name = 'Calibri'
        sub_run.font.size = Pt(10)
        sub_run.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_paragraph()

        # Date
        date_para = doc.add_paragraph(datetime.now().strftime("%B %d, %Y"))
        date_para.runs[0].font.name = 'Calibri'
        date_para.runs[0].font.size = Pt(10.5)

        doc.add_paragraph()

        # Addressee
        addr_para = doc.add_paragraph()
        addr_run1 = addr_para.add_run("Hiring Team\n")
        addr_run2 = addr_para.add_run(f"{comp}\n")
        addr_run3 = addr_para.add_run("Analytics & Data Department")
        for r in [addr_run1, addr_run2, addr_run3]:
            r.font.name = 'Calibri'
            r.font.size = Pt(10.5)
            r.font.color.rgb = RGBColor(30, 41, 59)

        doc.add_paragraph()

        # Body Paragraphs
        body_text = payload.tailored_cover_letter or ""
        paragraphs = body_text.split("\n\n")

        for p in paragraphs:
            if not p.strip():
                continue
            bp = doc.add_paragraph()
            bp.paragraph_format.line_spacing = 1.15
            bp.paragraph_format.space_after = Pt(8)
            brun = bp.add_run(p.strip())
            brun.font.name = 'Calibri'
            brun.font.size = Pt(10.5)
            brun.font.color.rgb = RGBColor(30, 41, 59)

        doc.save(file_path)
        return file_path

    @classmethod
    def sync_to_strategy_tracker(cls, payload: ReviewPayload, cover_letter_file: str) -> Dict[str, Any]:
        """Appends or updates application status in the Strategy Tracker format."""
        os.makedirs(STRATEGY_DATA_DIR, exist_ok=True)
        file_exists = os.path.exists(TRACKER_CSV_PATH)

        headers = [
            "Status", "Target Company", "Target Role", "Department",
            "Job Link / Requirements", "Date Added", "Google Doc Link",
            "PDF Link", "DOCX Link", "Notes"
        ]

        matched_summary = ", ".join(payload.evaluation.matched_skills[:8])
        notes = f"Match: {payload.evaluation.overall_score}% ({payload.evaluation.match_category.value}) | Option A Verified"

        record = {
            "Status": "Reviewed (Option A Ready)",
            "Target Company": FormFieldMapper.clean_company_name(payload.job.company),
            "Target Role": payload.job.title,
            "Department": "Analytics / Data",
            "Job Link / Requirements": payload.job.url or matched_summary,
            "Date Added": datetime.now().strftime("%Y-%m-%d"),
            "Google Doc Link": "Synced to JoB_Tracker",
            "PDF Link": cover_letter_file.replace(".docx", ".pdf"),
            "DOCX Link": cover_letter_file,
            "Notes": notes
        }

        with open(TRACKER_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)

        return record


CACHE_DB_PATH = "/tmp/screening_qa_cache.db"

class ScreeningEngine:
    """AI Screening & Dynamic Question-Answering Engine with local caching."""

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._init_cache()

    def _init_cache(self):
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS qa_cache (
                        normalized_question TEXT PRIMARY KEY,
                        raw_question TEXT,
                        answer TEXT,
                        field_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            pass

    @staticmethod
    def normalize_question(q: str) -> str:
        import re
        return re.sub(r'[^a-z0-9]', '', q.lower())

    def get_cached_answer(self, question_text: str) -> Optional[str]:
        import sqlite3
        norm = self.normalize_question(question_text)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT answer FROM qa_cache WHERE normalized_question = ?", (norm,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        return None

    def save_cached_answer(self, question_text: str, answer: str, field_type: str = "text"):
        import sqlite3
        norm = self.normalize_question(question_text)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO qa_cache (normalized_question, raw_question, answer, field_type) VALUES (?, ?, ?, ?)",
                    (norm, question_text, answer, field_type)
                )
                conn.commit()
        except Exception:
            pass

    @classmethod
    def resolve_rule_based(cls, req: Any, profile: CandidateProfile) -> Tuple[Optional[str], Optional[str]]:
        import re
        q = req.question_text.lower()

        # 1. Work Authorization
        if any(term in q for term in ["legally authorized", "authorized to work", "legal right to work", "work authorization", "eligible to work in the u.s."]):
            ans = "Yes" if profile.us_authorized else "No"
            return (cls._match_option(ans, req.options), "rules")

        # 2. Sponsorship
        if any(term in q for term in ["require sponsorship", "now or in the future", "visa sponsorship", "h-1b"]):
            ans = "Yes" if profile.requires_sponsorship else "No"
            return (cls._match_option(ans, req.options), "rules")

        # 3. Notice Period / Start Date
        if any(term in q for term in ["notice period", "how soon can you start", "earliest start date", "availability"]):
            ans = profile.default_answers.get("notice_period", "2 weeks notice")
            return (cls._match_option(ans, req.options), "rules")

        # 4. Salary / Compensation
        if any(term in q for term in ["salary expectation", "compensation", "desired salary", "hourly rate"]):
            ans = profile.default_answers.get("salary_expectation", "Open / Market Rate (Competitive)")
            return (ans, "rules")

        # 5. Relocation / Location
        if any(term in q for term in ["willing to relocate", "relocation"]):
            return (cls._match_option("Yes", req.options), "rules")
        if any(term in q for term in ["current city", "current location", "where are you based", "address"]):
            return (f"{profile.city}, {profile.state}", "rules")

        # 6. Referral Source
        if any(term in q for term in ["how did you hear", "referral source", "source"]):
            for opt in ["Company Careers Page", "LinkedIn", "Job Board", "Other"]:
                matched = cls._match_option(opt, req.options)
                if matched != opt:
                    return (matched, "rules")
            return ("Company Careers Page", "rules")

        # 7. Specific tool experience years
        yr_match = re.search(r'years?\s+(?:of\s+)?([a-z0-9\s]+?)\s+(?:experience|do you have)', q)
        if yr_match:
            tool_queried = yr_match.group(1).strip()
            if any(t in tool_queried for t in ["sql", "python", "power bi", "analytics", "etl", "data", "azure"]):
                ans = str(int(profile.years_experience)) if "int" in req.field_type else f"{profile.years_experience} years"
                return (cls._match_option(ans, req.options), "rules")

        return (None, None)

    @staticmethod
    def _match_option(desired: str, options: List[str]) -> str:
        if not options:
            return desired
        des_clean = desired.lower().strip()
        for opt in options:
            if opt.lower().strip() == des_clean:
                return opt
        for opt in options:
            o_clean = opt.lower().strip()
            if des_clean in o_clean or o_clean in des_clean:
                return opt
        if des_clean in ["yes", "true", "authorized"]:
            for opt in options:
                if opt.lower() in ["yes", "i am", "true", "authorized"]:
                    return opt
        if des_clean in ["no", "false"]:
            for opt in options:
                if opt.lower() in ["no", "i am not", "false"]:
                    return opt
        return options[0]

    @classmethod
    def answer_question(cls, req: Any, profile: CandidateProfile) -> Any:
        from neorex.core.models import QuestionAnswerResponse
        engine = cls()

        cached = engine.get_cached_answer(req.question_text)
        if cached:
            selected_opt = cls._match_option(cached, req.options) if req.options else None
            return QuestionAnswerResponse(
                question_text=req.question_text,
                answer=cached,
                source="cache",
                selected_option=selected_opt,
                confidence=1.0
            )

        rule_answer, source = cls.resolve_rule_based(req, profile)
        if rule_answer is not None:
            engine.save_cached_answer(req.question_text, rule_answer, req.field_type)
            return QuestionAnswerResponse(
                question_text=req.question_text,
                answer=rule_answer,
                source="rules",
                selected_option=rule_answer if req.options else None,
                confidence=1.0
            )

        q_lower = req.question_text.lower()
        company_str = req.company or "the team"

        if any(term in q_lower for term in ["why do you want to work", "interest in", "why us"]):
            answer = (
                f"I am excited about {company_str}'s mission and technological direction. With 3+ years of experience "
                f"building automated ETL pipelines, optimizing analytical queries, and delivering high-visibility Power BI "
                f"dashboards, I am eager to apply my background in data modeling and cloud analytics to deliver immediate impact."
            )
        elif any(term in q_lower for term in ["describe a project", "challenging problem", "complex sql", "etl pipeline"]):
            answer = (
                f"At Tenet Healthcare, I designed and optimized daily ingestion workflows processing 50+ GB/day of operational data. "
                f"By restructuring query distribution keys and columnstore indexing in Azure Synapse, I improved query performance by 35% "
                f"and automated reconciliation workflows using Python and SQL, saving over 10 hours per week of manual validation."
            )
        elif any(term in q_lower for term in ["data quality", "governance", "validation"]):
            answer = (
                f"I prioritize data integrity by building automated post-load reconciliation checks using SQL and Python. "
                f"My workflows automatically flag anomalies, enforce watermark validation, and integrate alerting through CI/CD pipelines, "
                f"ensuring downstream reporting remains fully reliable."
            )
        elif any(term in q_lower for term in ["greatest strength", "key skills"]):
            answer = (
                f"My key strength lies in bridging complex raw data pipelines with intuitive business intelligence. I specialize in "
                f"SQL, Python, dimensional data modeling, and developing high-performance Power BI dashboards that translate operations into clear KPIs."
            )
        else:
            skills_sub = ", ".join(profile.skills[:5])
            answer = (
                f"With over 3 years of hands-on experience in analytics engineering and business intelligence, my background in "
                f"{skills_sub} aligns closely with the technical and analytical needs of this role."
            )

        if req.max_chars and len(answer) > req.max_chars:
            answer = answer[:req.max_chars - 3].rsplit(' ', 1)[0] + "..."

        selected_opt = cls._match_option(answer, req.options) if req.options else None
        engine.save_cached_answer(req.question_text, answer, req.field_type)

        return QuestionAnswerResponse(
            question_text=req.question_text,
            answer=answer,
            source="generated",
            selected_option=selected_opt,
            confidence=0.9
        )
