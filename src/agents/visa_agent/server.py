from __future__ import annotations

from typing import Dict, Any

from src.utils.config import Settings
from src.utils.logger import get_logger
from .tools import VisaTools


class VisaMCPServer:
    """MCP server facade for visa/document guidance."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("visa_mcp")
        self.tools = VisaTools(settings)

    def synthesize_guidance(self, params: Dict[str, Any]) -> str:
        return self.tools.synthesize(params)