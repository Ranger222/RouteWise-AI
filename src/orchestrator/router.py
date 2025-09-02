"""MCP router for workflow selection"""
from __future__ import annotations

import os
from typing import Literal, Optional

from src.utils.logger import get_logger
from .workflow import MCPWorkflow


class MCPRouter:
    """Router that can switch between legacy and MCP workflows"""
    
    def __init__(self):
        self.logger = get_logger("mcp_router")
        self.mode: Literal["legacy", "mcp"] = os.getenv("ROUTEWISE_MODE", "mcp").lower()  # Default to MCP
        
        if self.mode not in ("legacy", "mcp"):
            self.logger.warning(f"Invalid mode '{self.mode}', defaulting to MCP")
            self.mode = "mcp"
        
        self.logger.info(f"Router initialized in {self.mode} mode")
    
    def route(
        self, 
        query: str, 
        save: bool = True,
        session_id: Optional[str] = None,
        memory_manager: Optional[object] = None,
        message_type: str = "text",
    ) -> str:
        """Route to appropriate workflow based on mode"""
        if self.mode == "mcp":
            workflow = MCPWorkflow()
            return workflow.run(
                query=query, 
                save=save,
                session_id=session_id,
                memory_manager=memory_manager,
                message_type=message_type,
            )
        else:
            # Legacy mode - import original orchestrator
            from src.orchestrator import Orchestrator
            legacy_orch = Orchestrator()
            return legacy_orch.run(query, save=save)