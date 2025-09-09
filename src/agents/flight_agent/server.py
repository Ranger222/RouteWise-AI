from __future__ import annotations

from typing import Dict, Any

from src.utils.config import Settings
from src.utils.logger import get_logger
from .tools import FlightTools


class FlightMCPServer:
    """MCP server facade for flight suggestions."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("flight_mcp")
        self.tools = FlightTools(settings)

    # Simple, consistent interface similar to other servers
    def suggest_flights(self, params: Dict[str, Any]) -> str:
        return self.tools.suggest(params)