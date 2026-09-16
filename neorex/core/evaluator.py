"""
Job Role Evaluation Engine (v2.0 - High Precision NLP & Clustered Scoring).
Analyzes Job Postings against Candidate Profiles, computes nuanced alignment scores,
handles alternative tool clusters (e.g., AWS or Azure, Power BI or Tableau),
and isolates genuine qualification sections from company background and EEO disclosures.
"""

import re
from typing import List, Tuple, Set, Dict, Optional
from neorex.core.models import (
    CandidateProfile, JobPosting, EvaluationReport, MatchCategory
)

# Comprehensive Taxonomy of 200+ Industry Competencies, Platforms, and Data Concepts
TAXONOMY = {
    # Languages & Querying
    "sql": ["sql", "structured query language"],
    "t-sql": ["t-sql", "tsql", "transact-sql"],
    "pl/sql": ["pl/sql", "plsql"],
    "python": ["python"],
    "r": ["r programming", r"\br\b"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "pyspark": ["pyspark"],
    "scala": ["scala"],
    "bash": ["bash", "shell scripting"],

    # BI, Analytics & Visualization
    "power bi": ["power bi", "powerbi", "pbi"],
    "dax": ["dax", "data analysis expressions"],
    "power query": ["power query", "powerquery", "m language"],
    "tableau": ["tableau"],
    "looker": ["looker", "lookml"],
    "sigma": ["sigma", "sigma computing"],
    "quicksight": ["quicksight"],
    "excel": ["excel", "advanced excel", "ms excel", "spreadsheets"],
    "vba": ["vba", "macros"],
    "power automate": ["power automate", "power platform"],
    "dashboards": ["dashboards", "dashboard development", "dashboard reporting"],
    "reporting": ["reporting", "analytical reporting", "business reporting", "kpis", "metrics"],
    "business intelligence": ["business intelligence", r"\bbi\b"],

    # Cloud Platforms & Data Warehouses
    "azure": ["azure", "microsoft azure"],
    "azure synapse": ["azure synapse", "synapse analytics", "azure dw", "synapse"],
    "azure data factory": ["azure data factory", "adf"],
    "adls": ["adls", "adls gen2", "azure data lake"],
    "aws": ["aws", "amazon web services"],
    "s3": ["amazon s3", r"\bs3\b"],
    "redshift": ["redshift", "amazon redshift"],
    "athena": ["athena", "amazon athena"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "bigquery": ["bigquery", "google bigquery"],
    "snowflake": ["snowflake", "snowflake data cloud"],
    "databricks": ["databricks"],
    "delta lake": ["delta lake", "lakehouse"],
    "fabric": ["microsoft fabric", "fabric"],

    # Data Engineering, Modeling & ETL
    "etl": ["etl", "extract transform load"],
    "elt": ["elt", "extract load transform"],
    "data pipelines": ["data pipelines", "pipeline development", "data ingestion"],
    "data modeling": ["data modeling", "data model", "data schemas"],
    "dimensional modeling": ["dimensional modeling", "star schema", "snowflake schema", "kimball"],
    "data warehouse": ["data warehouse", "data warehousing", "edw"],
    "data quality": ["data quality", "data validation", "data reconciliation", "reconciliation"],
    "data governance": ["data governance", "data integrity", "data stewardship"],
    "dbt": ["dbt", "data build tool"],
    "apache airflow": ["airflow", "apache airflow"],
    "ssis": ["ssis", "sql server integration services"],
    "ssrs": ["ssrs", "sql server reporting services"],
    "kafka": ["kafka", "apache kafka"],
    "spark": ["spark", "apache spark"],
    "git": ["git", "github", "gitlab", "version control"],
    "ci/cd": ["ci/cd", "ci", "continuous integration", "pipelines"],

    # Domain & Methodologies
    "healthcare analytics": ["healthcare analytics", "healthcare data", "health systems"],
    "claims data": ["claims data", "healthcare claims", "medical claims", "cms claims"],
    "cms": ["cms", "centers for medicare"],
    "epic": ["epic", "epic systems"],
    "clarity": ["clarity", "epic clarity"],
    "caboodle": ["caboodle", "epic caboodle"],
    "cosmos": ["epic cosmos", "cosmos"],
    "hipaa": ["hipaa", "phi", "patient privacy"],
    "statistical analysis": ["statistical analysis", "statistics", "hypothesis testing"],
    "a/b testing": ["a/b testing", "experimentation", "cohort analysis"],
    "machine learning": ["machine learning", r"\bml\b", "predictive modeling"]
}

# Equivalence Clusters: Having ANY skill in a cluster satisfies an "OR" requirement
EQUIVALENCE_CLUSTERS = {
    "cloud_infrastructure": {"azure", "aws", "gcp"},
    "cloud_data_warehouse": {"snowflake", "azure synapse", "databricks", "redshift", "bigquery"},
    "bi_dashboard_platform": {"power bi", "tableau", "looker", "sigma", "quicksight"},
    "data_pipeline_orchestration": {"azure data factory", "apache airflow", "dbt", "ssis"},
    "relational_database": {"sql", "t-sql", "pl/sql", "mysql", "postgresql", "sql server"},
    "scripting_language": {"python", "r"}
}

class JobRoleEvaluator:
    """Evaluates alignment between CandidateProfile and JobPosting using semantic clustering."""

    @classmethod
    def extract_keywords_from_text(cls, text: str) -> Set[str]:
        """Scans text against taxonomy with regex word boundaries."""
        lower = text.lower()
        found = set()
        for canonical, patterns in TAXONOMY.items():
            for p in patterns:
                # If pattern is raw regex (starts with backslash or contains regex tokens)
                if "\\" in p or "^" in p:
                    if re.search(p, lower):
                        found.add(canonical)
                        break
                else:
                    escaped = re.escape(p)
                    if re.search(rf"(?:\b|\W){escaped}(?:\b|\W)", lower):
                        found.add(canonical)
                        break
        return found

    @classmethod
    def segment_job_description(cls, raw_text: str) -> Dict[str, str]:
        """Separates JD into functional sections: requirements, preferred, responsibilities, and noise."""
        lines = raw_text.splitlines()
        sections = {
            "required": [],
            "preferred": [],
            "responsibilities": [],
            "general": []
        }

        current_section = "general"

        req_headers = re.compile(r"^(?:(?:minimum|basic|key|core|job)\s+)?(?:requirements?|qualifications?|what you('ll)? (?:need|bring)|must haves?|who you are)", re.I)
        pref_headers = re.compile(r"^(?:preferred|bonus|nice to have|desired|preferred qualifications?|plus points?)", re.I)
        resp_headers = re.compile(r"^(?:responsibilities|what you('ll)? do|key duties|role overview|essential functions)", re.I)
        noise_headers = re.compile(r"^(?:about (?:us|the company)|who we are|equal (?:employment )?opportunity|benefits|perks|eeo|compensation)", re.I)

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            # Check if this line is a section header (usually short, under 60 chars)
            if len(trimmed) < 60:
                if req_headers.search(trimmed):
                    current_section = "required"
                    continue
                elif pref_headers.search(trimmed):
                    current_section = "preferred"
                    continue
                elif resp_headers.search(trimmed):
                    current_section = "responsibilities"
                    continue
                elif noise_headers.search(trimmed):
                    current_section = "noise"
                    continue

            if current_section != "noise":
                sections[current_section].append(trimmed)

        return {
            "required_text": "\n".join(sections["required"]),
            "preferred_text": "\n".join(sections["preferred"]),
            "responsibilities_text": "\n".join(sections["responsibilities"]),
            "general_text": "\n".join(sections["general"])
        }

    @classmethod
    def extract_years_experience(cls, segments: Dict[str, str], full_text: str) -> float:
        """Accurately extracts candidate required years of experience, avoiding company longevity noise."""
        # Prioritize scanning requirements & responsibilities first
        primary_text = segments["required_text"] + "\n" + segments["responsibilities_text"]
        if not primary_text.strip():
            # Exclude lines mentioning company age
            lines = [l for l in full_text.splitlines() if not re.search(r"\b(?:in business|serving|providing|founded|celebrating|industry leader)\b", l, re.I)]
            primary_text = "\n".join(lines)

        patterns = [
            # "3+ years of experience", "2 to 4 years experience", "3-5 years of data analysis experience"
            r'(\d+)\+?\s*(?:to|-)?\s*(\d+)?\s*years?(?:\s+of)?(?:\s+(?:professional|relevant|direct|working|prior))?\s+experience',
            r'minimum\s+(?:of\s+)?(\d+)\+?\s*years?',
            r'at\s+least\s+(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s+(?:in|with|demonstrated|hands-on)'
        ]

        found_years = []
        for p in patterns:
            matches = re.finditer(p, primary_text, re.IGNORECASE)
            for m in matches:
                val1 = m.group(1)
                if val1 and val1.isdigit():
                    yr = float(val1)
                    # Filter out unreasonable candidate requirements (e.g. 20+ years usually refers to company history)
                    if 1.0 <= yr <= 15.0:
                        found_years.append(yr)

        return min(found_years) if found_years else 0.0

    @classmethod
    def check_sponsorship_policy(cls, text: str) -> Tuple[Optional[str], bool]:
        lower = text.lower()
        blocked_phrases = [
            "no visa sponsorship", "sponsorship is not available",
            "not able to provide sponsorship", "unable to sponsor",
            "without the need for employer sponsorship", "must be a us citizen",
            "citizen or green card only", "no c2c", "w2 only"
        ]
        available_phrases = [
            "visa sponsorship available", "willing to sponsor",
            "provides visa sponsorship", "h-1b transfer accepted"
        ]
        for phrase in blocked_phrases:
            if phrase in lower:
                return ("Sponsorship Not Available", True)
        for phrase in available_phrases:
            if phrase in lower:
                return ("Sponsorship Available", False)
        return ("Unspecified / Disclosed upon inquiry", False)

    @classmethod
    def parse_job_description(cls, raw_text: str, title: str = "", company: str = "", url: str = "") -> JobPosting:
        segments = cls.segment_job_description(raw_text)

        # Extract skills from segmented sections
        req_skills = cls.extract_keywords_from_text(segments["required_text"])
        pref_skills = cls.extract_keywords_from_text(segments["preferred_text"])

        # If requirements section was not explicitly demarcated by headers, extract from responsibilities + general
        if not req_skills:
            all_extracted = cls.extract_keywords_from_text(segments["responsibilities_text"] + "\n" + segments["general_text"])
            req_skills = all_extracted
        else:
            # Also incorporate core technical skills mentioned in responsibilities
            resp_skills = cls.extract_keywords_from_text(segments["responsibilities_text"])
            req_skills.update(resp_skills)

        min_years = cls.extract_years_experience(segments, raw_text)
        sponsorship_policy, _ = cls.check_sponsorship_policy(raw_text)

        return JobPosting(
            id=f"job_{abs(hash(title + company + url)) % 1000000}",
            title=title or "Data & Analytics Role",
            company=company or "Prospective Employer",
            url=url,
            raw_text=raw_text,
            extracted_required_skills=sorted(list(req_skills)),
            extracted_preferred_skills=sorted(list(pref_skills)),
            extracted_min_years_exp=min_years,
            sponsorship_policy=sponsorship_policy
        )

    @classmethod
    def evaluate(cls, profile: CandidateProfile, job: JobPosting) -> EvaluationReport:
        candidate_skills = {s.lower() for s in profile.skills}
        # Automated parent implication for specialized tools
        if any('azure' in s for s in candidate_skills):
            candidate_skills.add('azure')
        if any('sql' in s for s in candidate_skills):
            candidate_skills.add('sql')
        if 'power bi' in candidate_skills or 'tableau' in candidate_skills:
            candidate_skills.update(['business intelligence', 'dashboards', 'reporting'])
        if 'pandas' in candidate_skills:
            candidate_skills.add('python')
        if any(w in candidate_skills for w in ['azure data factory', 'airflow', 'dbt', 'ssis']):
            candidate_skills.update(['data pipelines', 'etl'])
        for exp in profile.experiences:
            candidate_skills.update(cls.extract_keywords_from_text(" ".join(exp.highlights)))

        required_skills = {s.lower() for s in job.extracted_required_skills}
        preferred_skills = {s.lower() for s in job.extracted_preferred_skills}

        if not required_skills and not preferred_skills:
            required_skills = cls.extract_keywords_from_text(job.raw_text)

        # 1. Direct Skill Matching
        matched_req = candidate_skills.intersection(required_skills)
        missing_req = required_skills - candidate_skills

        # 2. Cluster / Alternative Equivalence Resolution:
        # If candidate misses an exact skill (e.g. AWS), but has an equivalent in the same cluster (e.g. Azure),
        # award equivalent cluster credit instead of heavily penalizing!
        equivalent_credits = set()
        for missing_skill in list(missing_req):
            for cluster_name, cluster_tools in EQUIVALENCE_CLUSTERS.items():
                if missing_skill in cluster_tools:
                    # Check if candidate has ANY other tool in this cluster
                    cand_cluster_overlap = candidate_skills.intersection(cluster_tools)
                    if cand_cluster_overlap:
                        equivalent_credits.add(missing_skill)
                        break

        # Adjust effective matched required
        effective_matched_req_count = len(matched_req) + (len(equivalent_credits) * 0.75)
        req_score = (effective_matched_req_count / len(required_skills) * 100) if required_skills else 100
        req_score = min(100.0, req_score)

        # 3. Preferred Skills Matching
        matched_pref = candidate_skills.intersection(preferred_skills)
        missing_pref = preferred_skills - candidate_skills
        pref_score = (len(matched_pref) / len(preferred_skills) * 100) if preferred_skills else 100

        # 4. Experience Tenure Alignment
        req_yrs = job.extracted_min_years_exp
        cand_yrs = profile.years_experience

        if req_yrs > 0:
            if cand_yrs >= req_yrs:
                exp_score = 100.0
                exp_summary = f"Strong tenure fit: Profile ({cand_yrs} yrs) meets/exceeds requirement ({req_yrs} yrs)."
            else:
                ratio = cand_yrs / req_yrs
                exp_score = max(50.0, ratio * 100.0)
                exp_summary = f"Tenure alignment: Profile has {cand_yrs} yrs vs {req_yrs} yrs requested."
        else:
            exp_score = 100.0
            exp_summary = f"Experience tenure open / candidate has {cand_yrs} yrs solid track record."

        # 5. Role Title Semantic Relevance
        title_lower = job.title.lower()
        role_bonus = 0.0
        if any(role_term in title_lower for role_term in ["analytics engineer", "data analyst", "bi developer", "data engineer", "business intelligence"]):
            role_bonus = 100.0
        else:
            role_bonus = 80.0

        # Weighted Composition:
        # 50% Required Technical Core, 20% Preferred Tools, 20% Tenure Fit, 10% Role Relevance
        overall_score = int(0.50 * req_score + 0.20 * pref_score + 0.20 * exp_score + 0.10 * role_bonus)
        overall_score = max(0, min(100, overall_score))

        # Eligibility Deal-Breakers
        warnings = []
        _, blocked = cls.check_sponsorship_policy(job.raw_text)
        if profile.requires_sponsorship and blocked:
            warnings.append("CRITICAL: Candidate requires visa sponsorship, but employer specifies no sponsorship available.")
            overall_score = min(overall_score, 45)

        if req_yrs > cand_yrs + 3.0:
            warnings.append(f"Seniority gap: Role requests {req_yrs} yrs (profile has {cand_yrs} yrs).")

        # True missing skills (exclude those with equivalent cluster coverage)
        true_missing_req = missing_req - equivalent_credits

        if overall_score >= 75 and not (profile.requires_sponsorship and blocked):
            category = MatchCategory.STRONG_MATCH
        elif overall_score >= 50:
            category = MatchCategory.MODERATE_MATCH
        else:
            category = MatchCategory.LOW_MATCH

        # Key Strengths
        key_strengths = []
        if matched_req:
            top_matched = sorted(list(matched_req))[:6]
            key_strengths.append(f"Core technical alignment across {', '.join(top_matched)}")
        if equivalent_credits:
            equiv_desc = [f"{s} (via {list(candidate_skills.intersection(EQUIVALENCE_CLUSTERS[c]))[0]})"
                          for s in list(equivalent_credits)[:2]
                          for c, tools in EQUIVALENCE_CLUSTERS.items() if s in tools]
            if equiv_desc:
                key_strengths.append(f"Transferable cluster competencies: {', '.join(equiv_desc)}")
        if exp_score == 100.0 and req_yrs > 0:
            key_strengths.append(f"Tenure matches target seniority level ({cand_yrs} yrs).")

        # Tailoring Recommendations
        recommendations = []
        if true_missing_req:
            recommendations.append(f"Address key required competencies in resume/cover letter: {', '.join(sorted(list(true_missing_req))[:4])}")
        if missing_pref:
            recommendations.append(f"Highlight adjacent project experience for preferred skills: {', '.join(sorted(list(missing_pref))[:3])}")

        top_skills = list(matched_req)[:4] if matched_req else ["SQL", "analytics engineering", "data pipelines"]
        hook = (
            f"Given {job.company}'s focus on {', '.join(top_skills)}, "
            f"my background in building robust data models, optimizing analytical pipelines, "
            f"and delivering actionable reporting enables me to contribute immediately."
        )

        return EvaluationReport(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            overall_score=overall_score,
            match_category=category,
            matched_skills=sorted(list(matched_req)),
            missing_required_skills=sorted(list(true_missing_req)),
            missing_preferred_skills=sorted(list(missing_pref)),
            experience_fit_summary=exp_summary,
            eligibility_warnings=warnings,
            key_strengths=key_strengths,
            improvement_recommendations=recommendations,
            suggested_custom_cover_letter_hook=hook
        )
