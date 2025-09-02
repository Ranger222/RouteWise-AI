from __future__ import annotations

from dataclasses import dataclass
from typing import List
import google.generativeai as genai

from src.utils.logger import get_logger
from src.utils.config import Settings
from src.agents.reality_miner_agent import Insight


@dataclass
class Itinerary:
    markdown: str


class ItineraryAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("itinerary")
        genai.configure(api_key=settings.gemini_api_key)
        # Prefer 1.5 Flash for speed in MVP; can be swapped to Pro
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def synthesize(self, query: str, insights: List[Insight]) -> Itinerary:
        # Group insights by type for structured inclusion
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
            "You are a pragmatic travel planner. Create a step-by-step, newbie-friendly Markdown itinerary using the user's request and the insights provided. "
            "Structure it clearly so a first-time traveler can follow it without confusion. Use short sentences and concrete instructions. "
            "Enrich with time-sensitive notes, real venues with approximate prices, and safety guidance. If sources disagree, advise verification on official sites. "
            "Include: a one-paragraph summary, day-by-day schedule with times, transport options with booking links/systems, budget line items, neighborhoods to target/avoid with 2 sample budget accommodations (name, ~price, link), a food & local experiences section, transport safety notes, and a closing checklist. "
            "Add a small 'Optional Swaps' section to adapt the plan for different preferences (culture vs shopping, etc.). "
            "Include dedicated sections for: Contextual Scams, Situational Pickpocket Warnings, Real Traveler Hacks, Hidden/Extra Costs, Time-Sensitive Notes, Food & Local Experiences, Sample Budget Stays, and Transport Safety. "
            "Do not invent facts; prefer instructions like 'verify on official site' and 'book via IRCTC/RedBus' when uncertain."
            f"\n\nUser Query: {query}\n\n"
            f"Contextual Scams (from insights):\n{scams}\n\n"
            f"Situational Pickpocket Warnings (from insights):\n{warns}\n\n"
            f"Real Traveler Hacks (from insights):\n{hacks}\n\n"
            f"Hidden/Extra Costs (from insights):\n{costs}\n\n"
            f"Time-Sensitive Notes (from insights):\n{temporals}\n\n"
            f"Food & Local Experiences (from insights):\n{foods}\n\n"
            f"Sample Budget Stays (from insights):\n{accos}\n\n"
            f"Transport Safety (from insights):\n{transport}\n\n"
            "Now write the final itinerary in Markdown with the following skeleton:\n"
            "## Trip Title\n\n"
            "### Summary\n(2-4 sentences)\n\n"
            "### Day-by-Day Plan\n"
            "- Day 1 Morning: ...\n- Day 1 Afternoon: ...\n- Day 1 Evening: ...\n- Day 2 Morning: ... (extend if needed)\n\n"
            "### Time-Sensitive Notes (when to go, closed days)\n"
            "- ...\n\n"
            "### Food & Local Experiences\n"
            "- ...\n\n"
            "### Sample Budget Stays (approx price, link)\n"
            "- ...\n\n"
            "### Transport & Booking\n"
            "- Trains: how to book (IRCTC), typical duration, classes, safety notes\n"
            "- Buses: how to book (RedBus, MakeMyTrip), safety notes\n"
            "- Local transport (Metro, autos): safety and negotiation tips\n\n"
            "### Budget Breakdown (per person)\n"
            "- Transport: ...\n- Accommodation: ...\n- Food: ...\n- Activities/Fees: ...\n- Misc: ...\n\n"
            "### Neighborhood Guide\n"
            "- Target: ... + two budget options (name, ~price, link)\n"
            "- Avoid: ...\n\n"
            "### Transport Safety Notes\n"
            "- ...\n\n"
            "### Optional Swaps\n"
            "- If you prefer culture: ...\n"
            "- If you prefer shopping: ...\n\n"
            "### Contextual Scams (⚠️)\n"
            "- ...\n\n"
            "### Situational Pickpocket Warnings (⚠️)\n"
            "- ...\n\n"
            "### Real Traveler Hacks (💡)\n"
            "- ...\n\n"
            "### Hidden/Extra Costs (₹)\n"
            "- ...\n\n"
            "### Checklist\n"
            "- [ ] Tickets booked (train/bus)\n- [ ] Accommodation confirmed\n- [ ] Offline maps downloaded\n- [ ] Small bills ready for autos/shops\n- [ ] Apps: IRCTC, RedBus, maps, translation, UPI\n"
        )
        try:
            resp = self.model.generate_content(prompt)
            text = resp.text or ""
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            text = "Itinerary generation failed. Please check API configuration."
        return Itinerary(markdown=text)