"""
Storage and Tracking Layer.
Supports SQLite database with automatic fallback to JSON persistence.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from neorex.core.models import (
    ReviewPayload, SubmissionResult, ReviewStatus, ATSPlatform
)

DEFAULT_DB_PATH = os.environ.get(
    "JOB_APPLY_DB_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "job_applications.db"
    )
)
BACKUP_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "job_applications.json"
)

class ApplicationTrackerDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH, json_backup_path: str = BACKUP_JSON_PATH):
        self.db_path = db_path
        self.json_backup_path = json_backup_path
        os.makedirs(os.path.dirname(self.json_backup_path), exist_ok=True)
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception:
            pass
        self._init_db()

    def _get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path)
            # Test if execution succeeds
            conn.execute("SELECT 1")
            conn.row_factory = sqlite3.Row
            return conn
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            # Fallback for network mounts that lack file locking
            self.db_path = "/tmp/job_applications.db"
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        application_id TEXT PRIMARY KEY,
                        job_id TEXT,
                        job_title TEXT,
                        company TEXT,
                        platform TEXT,
                        url TEXT,
                        match_score INTEGER,
                        match_category TEXT,
                        status TEXT,
                        review_notes TEXT,
                        tailored_cover_letter TEXT,
                        payload_json TEXT,
                        created_at TIMESTAMP,
                        reviewed_at TIMESTAMP,
                        submitted_at TIMESTAMP,
                        submission_result TEXT
                    )
                """)
                conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            self.db_path = "/tmp/job_applications.db"
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        application_id TEXT PRIMARY KEY,
                        job_id TEXT,
                        job_title TEXT,
                        company TEXT,
                        platform TEXT,
                        url TEXT,
                        match_score INTEGER,
                        match_category TEXT,
                        status TEXT,
                        review_notes TEXT,
                        tailored_cover_letter TEXT,
                        payload_json TEXT,
                        created_at TIMESTAMP,
                        reviewed_at TIMESTAMP,
                        submitted_at TIMESTAMP,
                        submission_result TEXT
                    )
                """)
                conn.commit()

    def _sync_to_json(self):
        """Saves current state to JSON file for easy human inspection and portability."""
        apps = self.list_applications(limit=500)
        try:
            with open(self.json_backup_path, "w") as f:
                json.dump(apps, f, indent=2, default=str)
        except Exception as e:
            print(f"[Warning] Failed to sync JSON backup: {e}")

    def save_review_payload(self, payload: ReviewPayload):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO applications (
                    application_id, job_id, job_title, company, platform, url,
                    match_score, match_category, status, review_notes,
                    tailored_cover_letter, payload_json, created_at, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.application_id,
                payload.job.id,
                payload.job.title,
                payload.job.company,
                payload.job.platform.value,
                payload.job.url,
                payload.evaluation.overall_score,
                payload.evaluation.match_category.value,
                payload.status.value,
                payload.review_notes,
                payload.tailored_cover_letter,
                payload.json(),
                payload.created_at.isoformat() if payload.created_at else datetime.utcnow().isoformat(),
                payload.reviewed_at.isoformat() if payload.reviewed_at else None
            ))
            conn.commit()
        self._sync_to_json()

    def record_submission(self, result: SubmissionResult):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications SET
                    status = ?,
                    submitted_at = ?,
                    submission_result = ?
                WHERE application_id = ?
            """, (
                ReviewStatus.SUBMITTED.value if result.status in ["SUCCESS", "MOCK_SUBMITTED"] else ReviewStatus.FAILED.value,
                result.timestamp.isoformat(),
                json.dumps(result.dict(), default=str),
                result.application_id
            ))
            conn.commit()
        self._sync_to_json()

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_applications(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
