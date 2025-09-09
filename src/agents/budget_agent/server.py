from __future__ import annotations

from typing import Dict, Any

from src.utils.config import Settings
from src.utils.logger import get_logger
from .tools import BudgetTools


class BudgetMCPServer:
    """MCP server facade for budget estimation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("budget_mcp")
        self.tools = BudgetTools(settings)

    def estimate_budget(self, params: Dict[str, Any]) -> str:
        return self.tools.estimate(params)