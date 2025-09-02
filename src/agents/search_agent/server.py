"""MCP Search Agent server (stub)
This module will expose MCP-compliant tools based on SearchTools.
"""
from __future__ import annotations

from src.utils.config import Settings, load_settings
from .tools import SearchTools


class SearchMCPServer:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.tools = SearchTools(self.settings)

    # TODO: expose MCP endpoints (e.g., with mcp library)
    def search_route(self, query: str):
        """Temporary direct method to keep parity while MCP transport is wired up."""
        return self.tools.search(query)