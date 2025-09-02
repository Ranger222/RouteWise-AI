"""MCP Itinerary Agent server (stub)
This module will expose MCP-compliant tools based on ItineraryTools.
"""
from __future__ import annotations

from typing import List
from src.utils.config import Settings, load_settings
from .tools import ItineraryTools, Itinerary
from src.agents.reality_miner_agent.tools import Insight


class ItineraryMCPServer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.tools = ItineraryTools(self.settings)

    # TODO: expose MCP endpoints
    def build_itinerary(self, query: str, insights: List[Insight]):
        """Temporary direct method to keep parity while MCP transport is wired up."""
        return self.tools.synthesize(query, insights)