from __future__ import annotations

from dataclasses import dataclass
from typing import List
import google.generativeai as genai

from src.utils.logger import get_logger
from src.utils.config import Settings
from src.agents.reality_miner_agent.tools import Insight


@dataclass
class Itinerary:
    markdown: str


class ItineraryTools:
    """Core itinerary synthesis for MCP Itinerary Agent"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("itinerary_mcp")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def synthesize(self, query: str, insights: List[Insight]) -> Itinerary:
        def fmt(kind: str) -> List[str]:
            return [
                f"- {i.summary} (source: {i.source_url})" + (f"\n  - Details: {i.details}" if i.details else "")
                for i in insights if i.type == kind
            ]
        hacks = "\n".join(fmt("hack")) or "- None found"
        scams = "\n".join(fmt("scam")) or "- None found"
        warns = "\n".join(fmt("warning")) or "- None found"
        costs = "\n".join(fmt("cost")) or "- None found"
        temporals = "\n".join(fmt("temporal")) or "- None found"
        foods = "\n".join(fmt("food")) or "- None found"
        accos = "\n".join(fmt("accommodation")) or "- None found"
        transport = "\n".join(fmt("transport_safety")) or "- None found"

        prompt = (
            "You are RouteWise, a friendly, practical travel buddy. Write a helpful Markdown response tailored to the user's request and the insights provided. "
            "Tone: warm, concise, and human — like a savvy friend. Avoid rigid templates and repetition. Vary section names and keep it crisp. "
            "Prefer direct instructions over generic fluff. Use second person ('you')."
            "\n\nOutput rules:\n"
            "- Return ONLY Markdown, no preambles.\n"
            "- Default length 250–600 words unless the user explicitly asks for deep detail.\n"
            "- If the user did NOT ask for a day-by-day plan, DON'T force a long day-by-day.\n"
            "- Never invent a duration; adapt to the user's stated days. If unclear, suggest 2–3 duration options (e.g., weekend, 4–5 days).\n"
            "- If a section is irrelevant or you lack data, omit it — keep it lean.\n"
            "\nSuggested structure (adapt naturally — don't make it robotic):\n"
            "- Plan at a glance: 2–3 lines with the overall vibe and best timing.\n"
            "- Smart picks: neighborhood(s) to stay, a couple of standout things to do/eat (with approx prices when useful).\n"
            "- Getting around: concrete booking systems (IRCTC, RedBus, metro cards), typical times, quick safety tips.\n"
            "- Budget ballpark (optional): rough per-person ranges if the query implies budget.\n"
            "- Heads‑up: compact list merging scams, warnings, extra costs, and any time‑sensitive notes from insights.\n"
            "- Next steps: 2–3 bullets to move forward (book X, check Y, confirm Z).\n"
            "- Only if requested: Day‑by‑day for the asked number of days — short and actionable.\n"
            "\nFacts & safety:\n"
            "- Use real systems (IRCTC, RedBus) and say 'verify on official sites' when unsure.\n"
            "- Avoid long tables; keep bullets clean with 0–2 links if really helpful.\n"
            f"\nUser Query:\n{query}\n\n"
            f"Relevant insights (for your reasoning — weave them into the response naturally, don't dump them verbatim):\n"
            f"- Scams:\n{scams}\n\n"
            f"- Warnings:\n{warns}\n\n"
            f"- Hacks:\n{hacks}\n\n"
            f"- Hidden/Extra Costs:\n{costs}\n\n"
            f"- Time‑Sensitive Notes:\n{temporals}\n\n"
            f"- Food & Local Experiences:\n{foods}\n\n"
            f"- Budget Stays:\n{accos}\n\n"
            f"- Transport Safety:\n{transport}\n\n"
            "Finish with a single friendly question that helps me confirm or refine the plan."
        )
        try:
            resp = self.model.generate_content(prompt)
            text = resp.text or ""
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            text = "Itinerary generation failed. Please check API configuration."
        return Itinerary(markdown=text)