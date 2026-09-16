"""
Adapter Registry.
Routes a given career page URL/HTML to the correct ATS adapter.
"""

from typing import Optional, List
from neorex.adapters.base import BasePortalAdapter
from neorex.adapters.greenhouse import GreenhouseAdapter
from neorex.adapters.lever import LeverAdapter
from neorex.adapters.ashby import AshbyAdapter
from neorex.adapters.generic import GenericAdapter, WorkdayAdapter
from neorex.core.models import ATSPlatform

class AdapterRegistry:
    def __init__(self):
        self.adapters: List[BasePortalAdapter] = [
            GreenhouseAdapter(),
            LeverAdapter(),
            AshbyAdapter(),
            WorkdayAdapter(),
            GenericAdapter()  # Fallback
        ]

    def get_adapter_for_url(self, url: str, html: str = "") -> BasePortalAdapter:
        for adapter in self.adapters:
            if adapter.detect(url, html):
                return adapter
        return GenericAdapter()

    def get_adapter_by_platform(self, platform: ATSPlatform) -> BasePortalAdapter:
        for adapter in self.adapters:
            if adapter.platform == platform:
                return adapter
        return GenericAdapter()
