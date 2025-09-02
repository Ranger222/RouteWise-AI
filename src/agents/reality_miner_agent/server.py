"""MCP Reality Miner Agent server (stub)
This module will expose MCP-compliant tools based on RealityMinerTools.
"""
from __future__ import annotations

from typing import List, Dict, Any
from src.utils.config import Settings, load_settings
from .tools import RealityMinerTools, Insight


class RealityMinerMCPServer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.tools = RealityMinerTools(self.settings)

    # TODO: expose MCP endpoints
    def extract(self, query: str, documents: List[Dict[str, Any]]):
        """Temporary direct method to keep parity while MCP transport is wired up."""
        return self.tools.extract_insights(query, documents)