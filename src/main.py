"""RouteWise AI - Main CLI entrypoint
Provides direct access to MCP workflow via simple command line interface.
For enhanced interactive CLI, use: python -m src.clients.cli_client
"""
from __future__ import annotations

import argparse
import re
from src.utils.logger import get_logger
from src.orchestrator.router import MCPRouter
# Added imports for session-aware execution
from src.utils.config import load_settings
from src.orchestrator.memory import MemoryManager


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for main entrypoint"""
    p = argparse.ArgumentParser(
        description="RouteWise AI - Travel Planning with MCP Agents",
        epilog="For interactive mode: python -m src.clients.cli_client"
    )
    p.add_argument("query", type=str, help="Travel query, e.g., 'Delhi to Jaipur, 2 days, budget'")
    p.add_argument("--no-save", action="store_true", help="Do not save outputs to files")
    # New optional arguments to enable session/memory plumbing from callers (e.g., Next.js API)
    p.add_argument("--session-id", type=str, default=None, help="Existing session id to use (optional)")
    p.add_argument("--message-type", type=str, default="text", help="Message type: text|refinement (optional)")
    return p.parse_args()


def _looks_like_memory_check(q: str) -> bool:
    """Heuristic to detect general chat about remembering or chat history.
    This avoids running the full itinerary workflow for questions like
    'Do you remember the last chats?'.
    """
    lc = q.strip().lower()
    patterns = [
        r"\bremember\b.*\b(chat|chats|conversation|messages|history|last time)\b",
        r"\b(last\s+chats?|previous\s+(chat|conversation|messages|history))\b",
        r"\b(do you|can you)\s*(still\s*)?(remember|recall)\b",
        r"\bwhat\s+did\s+we\s+(talk|discuss|say)\s+last\s+time\b",
        r"\bshow\s+(me\s+)?(our\s+)?(chat|conversation)\s+history\b",
    ]
    return any(re.search(p, lc) for p in patterns)


def _build_memory_reply(memory: MemoryManager, session_id: str, user_query: str) -> str:
    """Create a concise, friendly reply for memory-check questions.
    Keeps the tone like a travel buddy and avoids itinerary formatting.
    """
    # Persist the user's memory-check message as part of the conversation
    memory.add_message(session_id, role="user", content=user_query, message_type="text")

    history = memory.get_conversation_history(session_id, limit=6)
    has_prior = len(history) > 1  # besides the message we just added

    if not has_prior:
        reply = (
            "Yes, I can remember messages within a session — but we haven't chatted before in this session yet. "
            "Tell me your destination, days, and budget, and I'll be right on it!"
        )
    else:
        # Build a short recap of the last few exchanges (excluding the message we just added)
        recent = [m for m in history[:-1]][-3:]
        bullets = []
        for m in recent:
            who = "You" if m.role == "user" else "Me"
            preview = (m.content or "").strip()
            if len(preview) > 100:
                preview = preview[:100] + "..."
            bullets.append(f"- {who}: {preview}")
        reply = (
            "Yes — I remember our recent chat. Here's a quick recap of the last few messages:\n\n"
            + ("\n".join(bullets) if bullets else "(It was pretty short!)")
            + "\n\nIf you'd like, I can pick up where we left off or make changes to your plan."
        )

    # Persist the assistant reply as a simple text message (not an itinerary)
    memory.add_message(session_id, role="assistant", content=reply, message_type="text")

    return reply


def main():
    logger = get_logger("main")
    args = parse_args()
    router = MCPRouter()

    # Initialize settings and memory manager for context-aware planning
    settings = load_settings()
    memory = MemoryManager(settings)

    # Reuse session if provided; otherwise create a new ephemeral session so the workflow can persist context
    if args.session_id:
        # Ensure the provided session exists (e.g., coming from Next.js chatId)
        memory.ensure_session_exists(args.session_id, initial_query=args.query if args.message_type == "text" else None)
        session_id = args.session_id
    else:
        session_id = memory.create_session(initial_query=args.query)

    # Deterministic pre-check: if it's a memory/general-chat question, answer directly
    if _looks_like_memory_check(args.query):
        reply_md = _build_memory_reply(memory, session_id, args.query)
        print("\n=== Final Itinerary (Markdown) ===\n")
        print(reply_md)
        return

    md = router.route(
        args.query,
        save=(not args.no_save),
        session_id=session_id,
        memory_manager=memory,
        message_type=args.message_type,
    )
    print("\n=== Final Itinerary (Markdown) ===\n")
    print(md)


if __name__ == "__main__":
    main()