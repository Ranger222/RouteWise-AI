from __future__ import annotations

from typing import Dict, Any

from mistralai import Mistral

from src.utils.logger import get_logger
from src.utils.config import Settings


class VisaTools:
    """Visa/document guidance synthesizer using web search context provided by Search agent upstream.
    This tool does not perform live HTTP; it writes general, country-agnostic guidance when details are unknown.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("visa_mcp")
        self.client = Mistral(api_key=settings.mistral_api_key)

    def synthesize(self, params: Dict[str, Any]) -> str:
        origin = params.get("origin_country") or params.get("origin_city") or "your country"
        dest = params.get("destination_country") or params.get("destination_city") or "destination country"
        days = params.get("trip_days") or "unknown"
        ft = params.get("first_time", False)

        system = (
            "You are a visa/document checklist advisor. Return ONLY Markdown.\n"
            "If nationality-specific rules are unknown, give safe, general steps and official sources to check.\n"
            "Keep it concise (80-150 words)."
        )
        user = (
            f"Origin/Nationality: {origin}\nDestination: {dest}\nTrip length: {days} days\nFirst-time traveler: {ft}"
        )
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
            self.logger.warning(f"Mistral visa synth failed: {e}")
            text = (
                "- Check official immigration website of the destination and your foreign ministry.\n"
                "- Ensure passport validity (6+ months), return/onward ticket, proof of funds, and accommodation.\n"
                "- Consider travel insurance; verify e-visa/visa-on-arrival requirements."
            )
        return text.strip()