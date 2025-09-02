from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
from mistralai import Mistral

from src.utils.logger import get_logger
from src.utils.config import Settings


@dataclass
class Insight:
    type: str  # scam | warning | hack | cost | delay | complaint | temporal | food | accommodation | transport_safety
    summary: str
    details: str | None
    source_url: str | None


class RealityMinerAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("miner")
        self.client = Mistral(api_key=settings.mistral_api_key)

    def extract_insights(self, query: str, documents: List[Dict[str, Any]]) -> List[Insight]:
        # Prepare prompt
        combined = []
        for d in documents:
            content = d.get("content") or d.get("snippet") or ""
            if not content:
                continue
            combined.append(f"SOURCE: {d.get('url','')}\nTITLE: {d.get('title','')}\nTEXT: {content[:4000]}")
        big_context = "\n\n".join(combined)[:12000]

        system = (
            "You are a reality miner that extracts practical travel risks and tips. "
            "From the provided web content, extract a JSON array of insights with fields: type (one of scam, warning, hack, cost, delay, complaint, temporal, food, accommodation, transport_safety), summary, details, source_url. "
            "Write summaries that are specific and contextualized (include the place/situation and the behavior to watch for). Prefer concrete, verifiable warnings over generic advice. "
            "Examples of the desired style: \n"
            "- temporal: Amer Fort is least crowded before 9:30 AM; Johari Bazaar shops are closed on Sundays.\n"
            "- accommodation: Zostel Jaipur (MI Road area) ~₹600-900 per bed; GoStops Jaipur ~₹700-1000 — check recent reviews before booking.\n"
            "- food: Try Lassiwala near MI Road (₹50) for authentic lassi; avoid golgappa from unlicensed carts near Hawa Mahal.\n"
            "- transport_safety: Jaipur autos often refuse the meter — insist on meter or use Ola/Uber; avoid night buses if solo, prefer AC trains/day buses.\n"
            "- scam: At Jaipur Railway Station, some drivers claim your hotel is 'closed' to redirect you for commission; call the hotel before agreeing.\n"
            "- warning: Pickpocketing is common at Hawa Mahal and Johari Bazaar when bargaining; keep wallets in front pockets or use a money belt.\n"
            "- hack: Amer Fort: Use the back gate to avoid queues; Hawa Mahal: Best photo from Wind View Café (coffee ~₹150).\n"
            "- cost: City Palace: Photography in open courtyards is free; extra fees apply only for restricted sections.\n"
            "Keep items concise and actionable. Ignore fluff."
        )
        user = (
            f"User Query: {query}\n\nContent to analyze:\n{big_context}\n\n"
            "Return strictly valid JSON array with 8-20 items including a mix across types, with sources when possible."
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
            # Try multiple response shapes for robustness across versions
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)
        except Exception as e:
            self.logger.error(f"Mistral API error: {e}")
            return []

        import json
        try:
            data = json.loads(content)
        except Exception:
            # Try bracket slicing first
            start = content.find("[")
            end = content.rfind("]")
            sliced = content[start : end + 1] if (start != -1 and end != -1 and end > start) else content
            # Attempt json_repair to fix minor issues (invalid control chars, trailing commas, quotes)
            try:
                from json_repair import repair_json

                repaired = repair_json(sliced)
                data = json.loads(repaired)
            except Exception as e2:
                self.logger.error(f"Failed to parse insights JSON: {e2}")
                return []

        # Normalize to list
        items = data if isinstance(data, list) else data.get("items", [])
        insights: List[Insight] = []
        for it in items:
            insights.append(
                Insight(
                    type=it.get("type", "warning"),
                    summary=it.get("summary", ""),
                    details=it.get("details"),
                    source_url=it.get("source_url"),
                )
            )
        return insights