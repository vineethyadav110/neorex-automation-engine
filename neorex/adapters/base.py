"""
Base Portal Adapter.
Defines standard lifecycle for detecting no-sign-in portals, extracting DOM fields,
generating client-side autofill scripts, and executing application submissions.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from neorex.core.models import (
    ReviewPayload, SubmissionResult, FormField, ATSPlatform, ReviewStatus
)

class BasePortalAdapter(ABC):
    platform: ATSPlatform = ATSPlatform.GENERIC

    @abstractmethod
    def detect(self, url: str, html: str = "") -> bool:
        """Determines whether the page belongs to this ATS."""
        pass

    @abstractmethod
    def generate_autofill_script(self, payload: ReviewPayload) -> str:
        """Generates safe JavaScript snippet to populate form fields directly in the browser DOM."""
        pass

    @abstractmethod
    def execute_submission(self, payload: ReviewPayload, dry_run: bool = True) -> SubmissionResult:
        """Submits the application payload. Enforces that review approval is verified before execution."""
        pass
