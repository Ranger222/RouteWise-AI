"""MCP Team Lead Agent server (stub)
This module exposes orchestration via TeamLeadTools.
"""
from __future__ import annotations

from src.utils.config import Settings
from .tools import TeamLeadTools


class TeamLeadMCPServer:
    def __init__(self, settings: Settings | None = None):
        # Fall back to environment-backed Settings via load_settings should be handled by caller
        # Here we require a Settings instance to avoid accidental empty init
        if settings is None:
            from src.utils.config import load_settings
            settings = load_settings()
        self.settings = settings
        self.tools = TeamLeadTools(self.settings)

    # Temporary direct method to keep parity while MCP transport is wired up
    def orchestrate(self, query: str, save: bool = True) -> str:
        return self.tools.orchestrate_workflow(query, save=save)