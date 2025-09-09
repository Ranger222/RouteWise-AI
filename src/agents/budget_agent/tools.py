from __future__ import annotations

from typing import Dict, Any

from mistralai import Mistral

from src.utils.config import Settings
from src.utils.logger import get_logger


class BudgetTools:
    """Coarse budget estimator: per-day and total ranges by destination and style."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("budget_mcp")
        self.client = Mistral(api_key=settings.mistral_api_key)

    def estimate(self, params: Dict[str, Any]) -> str:
        dest = params.get("destination_city") or params.get("destination_country") or "destination"
        days = int(params.get("trip_days") or 0)
        style = params.get("style") or "budget"
        is_domestic = bool(params.get("is_domestic", False))

        if is_domestic:
            system = (
                "You estimate domestic travel budgets within India. Return ONLY Markdown.\n"
                "Give per-day ranges in INR (₹) for budget and midrange, and a rough total for the given days.\n"
                "Mention main cost drivers (transport within city, food, lodging). Keep ~70-120 words."
            )
            user = f"Destination: {dest}\nDays: {days}\nStyle: {style}\nCurrency: INR"
        else:
            system = (
                "You estimate travel budgets. Return ONLY Markdown.\n"
                "Give per-day ranges (budget/midrange) and total estimate for the given days.\n"
                "Note assumptions and major cost drivers. Keep to ~80-130 words."
            )
            user = f"Destination: {dest}\nDays: {days}\nStyle: {style}"
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
            self.logger.warning(f"Mistral budget estimate failed: {e}")
            if is_domestic:
                if days:
                    text = (
                        f"- Budget: ₹{1200*days:,}-₹{2000*days:,} total (₹1,200–₹2,000/day)\n"
                        f"- Midrange: ₹{4000*days:,}-₹{7500*days:,} total (₹4,000–₹7,500/day)\n"
                        "- Major drivers: lodging, local transport (auto/ride-hailing), food."
                    )
                else:
                    text = (
                        "- Budget: ₹1,200–₹2,000/day; Midrange: ₹4,000–₹7,500/day (city dependent).\n"
                        "- Major drivers: lodging, local transport, food."
                    )
            else:
                if days:
                    text = (
                        f"- Budget: ${25*days}-{45*days} total (assuming $25-$45/day)\n"
                        f"- Midrange: ${60*days}-{100*days} total (assuming $60-$100/day)\n"
                        "- Major drivers: lodging, intercity transport, activities."
                    )
                else:
                    text = (
                        "- Budget: $25-$45/day; Midrange: $60-$100/day (varies by city).\n"
                        "- Major drivers: lodging, intercity transport, activities."
                    )
        return text.strip()