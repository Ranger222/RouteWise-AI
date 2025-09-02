"""MCP-based workflow orchestrator"""
from __future__ import annotations

from typing import Optional

from src.utils.logger import get_logger
from src.utils.config import load_settings
from src.agents.team_lead_agent.server import TeamLeadMCPServer
from src.orchestrator.memory import MemoryManager, TripContext


class MCPWorkflow:
    """MCP-based workflow that coordinates all agents via TeamLeadMCPServer"""
    
    def __init__(self):
        self.logger = get_logger("mcp_workflow")
        self.settings = load_settings()
        self.team_lead = TeamLeadMCPServer(self.settings)
    
    def run(
        self, 
        query: str, 
        save: bool = True,
        session_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None,
        message_type: str = "text",
    ) -> str:
        """Run complete MCP workflow
        If a memory manager and session id are provided, the conversation history will be
        used to augment the query and results will be persisted to the session.
        """
        self.logger.info("Starting MCP workflow orchestration")

        augmented_query = query
        if memory_manager and session_id:
            # Persist user message
            memory_manager.add_message(session_id, role="user", content=query, message_type=message_type)
            
            # Build concise context summary and augment the query
            context_summary = memory_manager.get_context_summary(session_id)
            augmented_query = f"{query}\n\n[Conversation Context]\n{context_summary}"

        # Execute orchestration
        result_markdown = self.team_lead.orchestrate(augmented_query, save=save)

        # Persist assistant response and update trip context
        if memory_manager and session_id:
            memory_manager.add_message(session_id, role="assistant", content=result_markdown, message_type="itinerary")
            
            # Update trip context (lightweight update)
            existing = memory_manager.get_trip_context(session_id)
            if existing is None:
                context = TripContext(
                    query=query,
                    destinations=[],
                    duration_days=0,
                    budget_range="",
                    preferences=[],
                    current_itinerary=result_markdown,
                    refinements=[query] if message_type == "refinement" else [],
                )
            else:
                existing.current_itinerary = result_markdown
                if message_type == "refinement":
                    existing.refinements.append(query)
                context = existing
            memory_manager.update_trip_context(session_id, context)
        
        return result_markdown