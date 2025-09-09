from __future__ import annotations

from typing import Dict, Any

from mistralai import Mistral

from src.utils.config import Settings
from src.utils.logger import get_logger


class ChecklistTools:
    """First-time traveler checklist including packing, SIM, arrival steps, money, apps."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("checklist_mcp")
        self.client = Mistral(api_key=settings.mistral_api_key)

    def build(self, params: Dict[str, Any]) -> str:
        dest = params.get("destination_city") or params.get("destination_country") or "your destination"
        days = params.get("trip_days") or "unknown"
        # accept both first_time and is_first_time
        ft = params.get("first_time", params.get("is_first_time", False))
        is_domestic = bool(params.get("is_domestic", False))

        if is_domestic:
            system = (
                "You are a practical domestic travel checklist assistant for trips within India. Return ONLY Markdown bullets.\n"
                "Do NOT mention passports, visas, or travel insurance.\n"
                "Focus on: government ID (Aadhaar/PAN/DL), phone + charger/power bank, UPI + some cash, eSIM/local data, IRCTC/RedBus apps,\n"
                "Ola/Uber and auto-rickshaw tips, arrival transport planning, essential meds, weather-specific clothing, and safety basics.\n"
                "Keep it tight (60-110 words)."
            )
        else:
            system = (
                "You are a practical packing and arrival checklist assistant. Return ONLY Markdown bullets.\n"
                "Focus on essentials: documents, money/cards, eSIM/SIM, chargers/adapters, meds, airport->city steps, safety.\n"
                "Keep it tight (70-140 words)."
            )

        user = f"Destination: {dest}\nLength: {days} days\nFirst time: {ft}\nDomestic trip: {is_domestic}"
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
            self.logger.warning(f"Mistral checklist build failed: {e}")
            if is_domestic:
                text = (
                    "- Valid ID (Aadhaar/PAN/DL); some cash + UPI set up.\n"
                    "- Phone, charger/power bank; offline maps.\n"
                    "- IRCTC/RedBus, Ola/Uber installed; plan arrival transport.\n"
                    "- Weather-appropriate clothing; basic meds; water bottle."
                )
            else:
                text = (
                    "- Passport, visa/eTA if required; travel insurance.\n"
                    "- eSIM or airport SIM; offline maps; power adapter.\n"
                    "- Notify bank; small cash; arrival transport planned."
                )
        return text.strip()