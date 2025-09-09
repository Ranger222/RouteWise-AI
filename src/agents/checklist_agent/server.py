from __future__ import annotations

from typing import Dict, Any

from src.utils.config import Settings
from src.utils.logger import get_logger
from .tools import ChecklistTools


class ChecklistMCPServer:
    """MCP server facade for first-time traveler checklist."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("checklist_mcp")
        self.tools = ChecklistTools(settings)

    def build_checklist(self, params: Dict[str, Any]) -> str:
        return self.tools.build(params)