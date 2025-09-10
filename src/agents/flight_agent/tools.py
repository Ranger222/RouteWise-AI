from __future__ import annotations

from typing import Dict, Any
from datetime import datetime

from mistralai import Mistral

from src.utils.logger import get_logger
from src.utils.config import Settings


class FlightTools:
    """Flight suggestion helper for MCP Flight Agent.
    Produces 2-3 sensible options based on origin/destination/dates without calling external flight APIs.
    Outputs concise Markdown with practical booking guidance.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("flight_mcp")
        self.client = Mistral(api_key=settings.mistral_api_key)

    def suggest(self, params: Dict[str, Any]) -> str:
        origin = params.get("origin_city") or "your city"
        dest = params.get("destination_city") or "your destination"
        d1 = params.get("depart_date") or "(pick your date)"
        d2 = params.get("return_date") or "(pick your date)"

        system = (
            "You are a pragmatic flight shopping assistant. Return ONLY Markdown. \n"
            "Give 2-3 likely-cheapest, reliable routing patterns and booking tips based on the cities/dates. \n"
            "No prices; suggest typical airlines and layover hubs. Encourage user to verify on Google Flights, Skyscanner, Kayak. \n"
            "Keep it short (80-150 words) and actionable."
        )
        user = (
            f"Origin: {origin}\nDestination: {dest}\nDepart: {d1}\nReturn: {d2}\n"
            "User prefers budget-friendly and reliable options when possible."
        )
        # Remove generic boilerplate: only include concise, context-aware content
        used_fallback = False
        try:
            resp = self.client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            try:
                text = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                text = getattr(resp, "output_text", "") or ""
        except Exception as e:
            self.logger.warning(f"Mistral flight suggest failed: {e}")
            used_fallback = True
            # Tighter fallback without verbose generic tips
            text = (
                "- Check Google Flights or Skyscanner; compare 1-stop options.\n"
                "- Avoid tight layovers (<2h) on outbound; verify baggage rules."
            )

        # Do not append static boilerplate; keep response lean
        return (text or "").strip()