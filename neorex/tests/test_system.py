"""
Automated Test Suite for Job Application System with Review Layer & Workday Engine.
"""

import unittest
from fastapi.testclient import TestClient
from neorex.core.models import (
    CandidateProfile, JobPosting, ATSPlatform, ReviewStatus, MatchCategory
)
from neorex.core.evaluator import JobRoleEvaluator
from neorex.core.review_layer import ReviewLayer
from neorex.adapters.registry import AdapterRegistry
from neorex.api.server import app

class TestJobApplicationSystem(unittest.TestCase):

    def setUp(self):
        self.profile = CandidateProfile(
            first_name="Vineeth Yadav",
            last_name="Kanneboina",
            email="vineethyadavk@gmail.com",
            phone="+1 (214) 492-3576",
            city="Dallas",
            state="TX",
            skills=["sql", "t-sql", "python", "power bi", "dax", "azure synapse", "azure data factory", "etl", "git", "dashboards", "reporting"],
            years_experience=3.5,
            us_authorized=True,
            requires_sponsorship=False,
            resume_path="Resume.docx"
        )
        self.client = TestClient(app)

    def test_adapter_detection(self):
        registry = AdapterRegistry()
        gh = registry.get_adapter_for_url("https://boards.greenhouse.io/company/jobs/123")
        self.assertEqual(gh.platform, ATSPlatform.GREENHOUSE)

        lev = registry.get_adapter_for_url("https://jobs.lever.co/company/456")
        self.assertEqual(lev.platform, ATSPlatform.LEVER)

        ash = registry.get_adapter_for_url("https://jobs.ashbyhq.com/company/789")
        self.assertEqual(ash.platform, ATSPlatform.ASHBY)

        wd = registry.get_adapter_for_url("https://target.myworkdayjobs.com/careers/job/Data-Analyst_R101")
        self.assertEqual(wd.platform, ATSPlatform.WORKDAY)

        gen = registry.get_adapter_for_url("https://careers.randomcompany.com/apply")
        self.assertEqual(gen.platform, ATSPlatform.GENERIC)

    def test_evaluator_high_match_with_clusters(self):
        jd_text = """
        National Trench Safety is hiring an Analytics Engineer.
        Qualifications:
        - 3+ years experience in data analytics or business intelligence.
        - Experience with a major cloud provider (AWS, Azure, or GCP).
        - Proficient with SQL and Python.
        - Knowledge of Power BI or Tableau for dashboards and reporting.
        """
        job = JobRoleEvaluator.parse_job_description(jd_text, "Analytics Engineer", "National Trench Safety")
        report = JobRoleEvaluator.evaluate(self.profile, job)
        self.assertGreaterEqual(report.overall_score, 75)
        self.assertEqual(report.match_category, MatchCategory.STRONG_MATCH)
        self.assertTrue("sql" in report.matched_skills)
        self.assertTrue("azure" in report.matched_skills)

    def test_evaluator_sponsorship_warning(self):
        candidate = self.profile.copy()
        candidate.requires_sponsorship = True

        jd_text = """
        Senior Data Engineer. Must have 5 years experience in Spark and Kafka.
        Important: No visa sponsorship provided for this role. Must be US Citizen or Green Card holder.
        """
        job = JobRoleEvaluator.parse_job_description(jd_text, "Senior Data Engineer", "DefenseCo")
        report = JobRoleEvaluator.evaluate(candidate, job)
        self.assertTrue(any("CRITICAL: Candidate requires visa sponsorship" in w for w in report.eligibility_warnings))
        self.assertLessEqual(report.overall_score, 45)

    def test_review_layer_workflow(self):
        jd_text = "Data Analyst position. SQL and Python required."
        job = JobRoleEvaluator.parse_job_description(jd_text, "Data Analyst", "DataLab")
        payload = ReviewLayer.prepare_review_payload(self.profile, job)

        self.assertEqual(payload.status, ReviewStatus.PENDING_REVIEW)
        self.assertFalse(ReviewLayer.is_eligible_for_submission(payload))

        payload = ReviewLayer.update_field_value(payload, "phone", "+1 999 888 7777")
        self.assertEqual(payload.status, ReviewStatus.USER_EDITED)

        payload = ReviewLayer.approve(payload, "Ready to go")
        self.assertEqual(payload.status, ReviewStatus.APPROVED)
        self.assertTrue(ReviewLayer.is_eligible_for_submission(payload))

        registry = AdapterRegistry()
        adapter = registry.get_adapter_by_platform(payload.job.platform)
        res = adapter.execute_submission(payload, dry_run=True)
        self.assertEqual(res.status, "MOCK_SUBMITTED")

    def test_screening_engine_endpoint(self):
        res = self.client.post("/api/screening/answer", json={
            "question_text": "Are you legally authorized to work in the United States?",
            "field_type": "select",
            "options": ["Yes, authorized", "No, need authorization"]
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["selected_option"], "Yes, authorized")

    def test_cover_letter_file_endpoint(self):
        req_data = {
            "title": "Analytics Engineer",
            "company": "National Trench Safety",
            "url": "https://boards.greenhouse.io/nationaltrenchsafety/jobs/101",
            "raw_jd_text": "Requires SQL, Python, Power BI, Azure."
        }
        prep_res = self.client.post("/api/review/prepare", json=req_data)
        self.assertEqual(prep_res.status_code, 200)
        app_id = prep_res.json()["application_id"]

        file_res = self.client.get(f"/api/strategy/cover_letter_file/{app_id}")
        self.assertEqual(file_res.status_code, 200)
        self.assertIn("application/vnd.openxmlformats", file_res.headers.get("content-type", ""))
        self.assertGreater(len(file_res.content), 1000)

if __name__ == "__main__":
    unittest.main()
