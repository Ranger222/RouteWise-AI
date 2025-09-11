from __future__ import annotations

from typing import Optional
import re
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.utils.logger import get_logger
from src.utils.config import load_settings
from src.orchestrator.memory import MemoryManager
from src.orchestrator.router import MCPRouter


logger = get_logger("api_server")
app = FastAPI(title="RouteWise AI Backend", version="0.1.0")

# Global, lightweight singletons for the app lifetime
settings = load_settings()
memory = MemoryManager(settings)
router = MCPRouter()


class PlanRequest(BaseModel):
  query: str
  sessionId: Optional[str] = None
  messageType: Optional[str] = "text"  # 'text' | 'refinement'
  fastMode: Optional[bool] = None  # optional per-request override


class PlanResponse(BaseModel):
  markdown: str


@app.get("/health")
def health():
  return {"status": "ok"}


@app.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
  q = (req.query or "").strip()
  if not q:
    raise HTTPException(status_code=400, detail="Missing 'query'")

  # Ensure/derive a session id
  session_id: Optional[str] = (req.sessionId or "").strip() or None
  try:
    if session_id:
      # Create the session row if it doesn't already exist
      memory.ensure_session_exists(session_id, initial_query=q if (req.messageType or "text") == "text" else None)
    else:
      session_id = memory.create_session(initial_query=q)
  except Exception as e:
    logger.warning(f"session init failed: {e}")

  # Short-circuit: memory-check style questions answered directly
  if _looks_like_memory_check(q):
    try:
      reply_md = _build_memory_reply(memory, session_id or "", q)
      return PlanResponse(markdown=reply_md)
    except Exception as e:
      logger.warning(f"memory reply failed, falling back to router: {e}")

  # Optional per-request FAST_MODE override (best-effort, restored after call)
  prev_fast = os.environ.get("FAST_MODE")
  try:
    if req.fastMode is not None:
      os.environ["FAST_MODE"] = "1" if req.fastMode else "0"

    md = router.route(
      q,
      save=False,  # do not write artifacts on server by default
      session_id=session_id,
      memory_manager=memory,
      message_type=(req.messageType or "text"),
    )
    return PlanResponse(markdown=md)
  except Exception as e:
    logger.error(f"planner error: {e}")
    raise HTTPException(status_code=500, detail="Planner failed")
  finally:
    # Restore previous FAST_MODE env to avoid affecting other requests
    if req.fastMode is not None:
      if prev_fast is None:
        os.environ.pop("FAST_MODE", None)
      else:
        os.environ["FAST_MODE"] = prev_fast


# ---- helpers (small duplication from CLI entry for web) ----
MEMORY_PATTERNS = [
  r"\bremember\b",
  r"\bmemory\b",
  r"\bwhat did (we|i) say\b",
  r"\brecap\b",
  r"\bhistory\b",
  r"\bdo you recall\b",
]


def _looks_like_memory_check(user_query: str) -> bool:
  t = (user_query or "").lower()
  return any(re.search(p, t) for p in MEMORY_PATTERNS)


def _build_memory_reply(memory: MemoryManager, session_id: str, user_query: str) -> str:
  # Persist the user's message first
  memory.add_message(session_id, role="user", content=user_query, message_type="text")

  history = memory.get_conversation_history(session_id, limit=6)
  has_prior = len(history) > 1

  if not has_prior:
    reply = (
      "Yes, I can remember messages within a session — but we haven't chatted before in this session yet. "
      "Tell me your destination, days, and budget, and I'll be right on it!"
    )
  else:
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

  # Persist the assistant reply
  memory.add_message(session_id, role="assistant", content=reply, message_type="text")
  return reply