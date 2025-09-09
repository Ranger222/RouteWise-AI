"""MCP-based workflow orchestrator"""
from __future__ import annotations

from typing import Optional
import re
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.config import load_settings
from src.agents.team_lead_agent.server import TeamLeadMCPServer
from src.orchestrator.memory import MemoryManager, TripContext
from mistralai import Mistral
from src.agents.search_agent.server import SearchMCPServer


class MCPWorkflow:
    """MCP-based workflow that coordinates all agents via TeamLeadMCPServer"""
    
    def __init__(self):
        self.logger = get_logger("mcp_workflow")
        self.settings = load_settings()
        self.team_lead = TeamLeadMCPServer(self.settings)
        # Mistral client for routing/classification to avoid hardcoded rules
        self.mistral = Mistral(api_key=self.settings.mistral_api_key)
        # Lightweight search server to support 'search' action without full itinerary synthesis
        self.search_server = SearchMCPServer(self.settings)

    def _is_general_chat(self, q: str) -> Optional[str]:
        """Detect common non-planning chat intents.
        Returns one of: 'memory', 'about', 'thanks', 'date', 'time', or None
        """
        lc = (q or "").strip().lower()
        # Memory/history style questions
        if re.search(r"\bremember\b.*\b(chat|chats|conversation|messages|history|last time)\b", lc) or \
           re.search(r"\b(last\s+chats?|previous\s+(chat|conversation|messages|history))\b", lc) or \
           re.search(r"\b(do you|can you)\s*(still\s*)?(remember|recall)\b", lc) or \
           re.search(r"\bwhat\s+did\s+we\s+(talk|discuss|say)\s+last\s+time\b", lc) or \
           re.search(r"\bshow\s+(me\s+)?(our\s+)?(chat|conversation)\s+history\b", lc):
            return "memory"
        # Date questions
        if re.search(r"\b(what\s+day\s+is\s+(it|today)|today'?s?\s+date|date\s+today|what\s+is\s+the\s+date)\b", lc):
            return "date"
        # Time questions
        if re.search(r"\b(what\s+time\s+is\s+it|current\s+time|time\s+now)\b", lc):
            return "time"
        # About/helper queries (restrict 'help' to bare/meta help, not travel help)
        travelish = any(w in lc for w in [
            "plan", "itinerary", "trip", "travel", "go to", "from ", " to ", "flight", "train", "bus",
            "hotel", "stay", "budget", "days", "date", "journey", "visa"
        ])
        if re.search(r"\b(who|what)\s+are\s+you\b", lc) or \
           re.search(r"\bwhat\s+can\s+you\s+do\b", lc) or \
           re.search(r"\b(how\s+do\s+you\s+work|capabilit|features)\b", lc) or \
           (re.fullmatch(r"\s*help\s*\??\s*", lc) is not None):
            return "about"
        # A broad 'help' shouldn't trigger meta/about if the query is clearly travel-related
        if ("help" in lc) and not travelish and len(lc) <= 60:
            return "about"
        # Gratitude
        if re.search(r"\b(thanks|thank you|ty|appreciate)\b", lc):
            return "thanks"
        return None

    def _build_chat_reply(self, kind: str, memory_manager: MemoryManager, session_id: str, query: str) -> str:
        """Build concise friendly replies for chat queries"""
        if kind == "memory":
            summary = memory_manager.get_context_summary(session_id)
            return f"Yep — here’s a quick recap of our recent chat:\n\n{summary if summary else 'No prior messages yet.'}"
        if kind == "date":
            now = datetime.now()
            day = now.strftime("%A")
            date_str = now.strftime("%B %d, %Y")
            return f"Today is {day}, {date_str}."
        if kind == "time":
            now = datetime.now()
            time_str = now.strftime("%I:%M %p").lstrip('0')
            return f"The current time is {time_str}."
        if kind == "about":
            return (
                "I'm RouteWise — your practical travel buddy. I can plan trips, refine or shorten plans, "
                "answer travel questions, and keep context across this session. Tell me a destination, days, "
                "budget, and interests, and I'll tailor it to you."
            )
        if kind == "thanks":
            return "You're welcome! Ready to plan the next step or adjust anything?"
        # Fallback generic buddy reply
        return (
            "I can help with travel planning or questions. Share your destination, dates, budget, and vibe (relaxing, food, nightlife, culture) — "
            "I'll put together something that fits."
        )

    def _route_with_mistral(
        self,
        query: str,
        memory_manager: Optional[MemoryManager],
        session_id: Optional[str],
    ) -> Optional[dict]:
        """Use Mistral to classify whether to respond directly or run the planner/search.
        Returns a dict like {action: direct|search|plan, direct_reply: str, reason: str} or None on failure.
        """
        try:
            # Build compact context for the router
            context_summary = ""
            recent_history = ""
            if memory_manager and session_id:
                context_summary = memory_manager.get_context_summary(session_id) or ""
                msgs = memory_manager.get_conversation_history(session_id, limit=4) or []
                pairs = []
                for m in msgs[-4:]:
                    role = "User" if m.role == "user" else "Assistant"
                    pairs.append(f"{role}: {m.content[:180]}")
                recent_history = " | ".join(pairs)

            system = (
                "You are the routing brain for a travel assistant. Decide if the input is general chat or "
                "answerable directly from conversation context, or if it truly needs external search/planning. "
                "Output STRICT JSON with keys: action, direct_reply, reason.\n"
                "- action: one of 'direct', 'search', 'plan'.\n"
                "- direct_reply: a concise 1-2 sentence friendly reply in Markdown when action='direct', else ''.\n"
                "Guidelines:\n"
                "- Choose 'direct' for small talk, chit-chat, meta-questions (about/help), date/time, memory/history, simple clarifications, or when the answer is obvious from context.\n"
                "- Choose 'search' only if accuracy requires external facts (e.g., live info, specific data you don't know).\n"
                "- Choose 'plan' only when the user is explicitly asking to create or heavily modify an itinerary.\n"
                "- NEVER fabricate itineraries for vague inputs. If unclear, prefer 'direct' with a clarifying nudge.\n"
            )
            user = (
                f"User Input: {query}\n\n"
                f"Context Summary: {context_summary}\n\n"
                f"Recent: {recent_history}"
            )

            resp = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
            )
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)

            import json
            try:
                data = json.loads(content)
            except Exception:
                # Attempt to slice JSON
                start = content.find("{")
                end = content.rfind("}")
                sliced = content[start : end + 1] if (start != -1 and end != -1 and end > start) else content
                try:
                    from json_repair import repair_json
                    repaired = repair_json(sliced)
                    data = json.loads(repaired)
                except Exception:
                    self.logger.warning("Router JSON parse failed; falling back to regex heuristics")
                    # As last resort, use prior lightweight heuristics
                    kind = self._is_general_chat(query)
                    if kind and memory_manager and session_id:
                        reply = self._build_chat_reply(kind, memory_manager, session_id, query)
                        return {"action": "direct", "direct_reply": reply, "reason": "heuristic-fallback"}
                    return None

            action = str(data.get("action", "")).strip().lower()
            direct_reply = data.get("direct_reply") or ""
            reason = data.get("reason") or ""
            if action not in ("direct", "search", "plan"):
                action = "direct" if direct_reply else "plan"
            return {"action": action, "direct_reply": direct_reply, "reason": reason}
        except Exception as e:
            self.logger.warning(f"Mistral routing failed: {e}")
            # Heuristic fallback
            kind = self._is_general_chat(query)
            if kind and memory_manager and session_id:
                reply = self._build_chat_reply(kind, memory_manager, session_id, query)
                return {"action": "direct", "direct_reply": reply, "reason": "exception-fallback"}
            return None

    def _answer_from_search(
        self,
        query: str,
        memory_manager: Optional[MemoryManager],
        session_id: Optional[str],
        max_results: int = 6,
    ) -> str:
        """Run a focused web search and craft a concise, direct answer without building an itinerary."""
        try:
            results = self.search_server.search_route(query) or []
            # Prepare compact evidence bundle
            lines = []
            for r in results[:max_results]:
                title = getattr(r, 'title', '') or (r.get('title') if isinstance(r, dict) else '')
                url = getattr(r, 'url', '') or (r.get('url') if isinstance(r, dict) else '')
                snippet = getattr(r, 'snippet', '') or (r.get('snippet') if isinstance(r, dict) else '')
                content = getattr(r, 'content', '') or (r.get('content') if isinstance(r, dict) else '')
                text = content or snippet or ''
                if text:
                    text = text.replace('\n', ' ').strip()[:500]
                lines.append(f"- {title} | {url}\n  {text}")
            evidence = "\n".join(lines)[:6000]

            system = (
                "You are a helpful travel assistant. Answer the user's query directly using the provided web snippets. "
                "Be concise (2-5 sentences or up to 5 bullets), practical, and avoid fluff. If the query is ambiguous, "
                "ask one clarifying question after a brief helpful note. Do NOT generate an itinerary here."
            )
            user = f"Question: {query}\n\nEvidence:\n{evidence}"

            resp = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)
            answer = content.strip() or "I found some info, but I need a bit more detail to answer precisely — what exactly would you like to know?"
        except Exception as e:
            self.logger.error(f"Search+answer failed: {e}")
            answer = "I couldn't fetch results right now. Could you rephrase or provide a bit more detail?"
        
        # Persist assistant response if memory is available
        if memory_manager and session_id:
            memory_manager.add_message(session_id, role="assistant", content=answer, message_type="text")
        return answer

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

            # LLM-based routing to avoid hardcoded edge cases
            route = self._route_with_mistral(query, memory_manager, session_id)
            if route and route.get("action") == "direct" and route.get("direct_reply"):
                reply = route["direct_reply"]
                memory_manager.add_message(session_id, role="assistant", content=reply, message_type="text")
                return reply
            if route and route.get("action") == "search":
                # Perform search-only answer and bypass itinerary pipeline entirely
                return self._answer_from_search(query, memory_manager, session_id)

            # Optionally pass routing hint in the augmented query (non-breaking)
            routing_hint = route.get("action") if route else None
            hint_text = f"\n\n[Routing Hint: {routing_hint}]" if routing_hint else ""
            augmented_query = f"{query}\n\n[Conversation Context]\n{context_summary}{hint_text}"

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