from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

from src.utils.logger import get_logger
from src.utils.config import load_settings
from src.agents.search_agent import SearchAgent, SearchResult
from src.agents.reality_miner_agent import RealityMinerAgent, Insight
from src.agents.itinerary_agent import ItineraryAgent


class Orchestrator:
    def __init__(self):
        self.logger = get_logger("orchestrator")
        self.settings = load_settings()
        self.search_agent = SearchAgent(self.settings)
        self.miner_agent = RealityMinerAgent(self.settings)
        self.itinerary_agent = ItineraryAgent(self.settings)

    def run(self, query: str, save: bool = True) -> str:
        self.logger.info("Starting workflow: Multi-Search → Mine → Synthesize")
        
        # Multi-query search strategy for comprehensive data collection
        search_queries = self._generate_search_queries(query)
        all_results: List[SearchResult] = []
        
        for search_query in search_queries:
            self.logger.info(f"Searching: {search_query}")
            results = self.search_agent.search(search_query)
            all_results.extend(results)
        
        # Deduplicate by URL across all searches
        seen = set()
        deduped: List[SearchResult] = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                deduped.append(r)
        
        docs: List[Dict[str, Any]] = [r.__dict__ for r in deduped if (r.content or r.snippet)]
        self.logger.info(f"Total unique documents collected: {len(docs)}")

        insights: List[Insight] = self.miner_agent.extract_insights(query, docs)
        itinerary = self.itinerary_agent.synthesize(query, insights)

        if save:
            self._save_outputs(query, deduped, insights, itinerary.markdown)
        return itinerary.markdown

    def _generate_search_queries(self, original_query: str) -> List[str]:
        """Generate targeted search queries for comprehensive travel data collection"""
        # Parse the original query to extract destinations and context
        queries = [original_query]  # Start with original
        
        # Extract key terms (simple parsing - could be enhanced with NLP)
        words = original_query.lower().split()
        destinations = []
        for word in words:
            if word.replace(',', '') in ['delhi', 'jaipur', 'mumbai', 'goa', 'kerala', 'rajasthan', 'agra', 'udaipur', 'jodhpur', 'pushkar']:
                destinations.append(word.replace(',', '').title())
        
        if not destinations:
            destinations = ['destination']  # Fallback
        
        primary_dest = destinations[-1] if destinations else 'destination'
        
        # Temporal insights queries
        queries.extend([
            f"{primary_dest} best time to visit attractions avoid crowds",
            f"{primary_dest} opening hours timings monuments museums",
            f"{primary_dest} shops markets closed days Sunday Monday",
            f"{primary_dest} rush hours traffic peak times avoid"
        ])
        
        # Accommodation queries
        queries.extend([
            f"{primary_dest} budget hostels zostel gostops backpacker accommodation",
            f"{primary_dest} cheap hotels guest houses budget stay under 1000",
            f"{primary_dest} accommodation near railway station city center"
        ])
        
        # Food & local experience queries
        queries.extend([
            f"{primary_dest} best local food restaurants lassi street food",
            f"{primary_dest} famous food joints must try dishes local cuisine",
            f"{primary_dest} food safety street food hygiene tips avoid",
            f"{primary_dest} authentic local restaurants hidden gems"
        ])
        
        # Transport safety and hacks
        queries.extend([
            f"{primary_dest} auto rickshaw scams meter fare negotiation tips",
            f"{primary_dest} local transport safety uber ola auto bus",
            f"{primary_dest} railway station taxi scams commission agents",
            f"{primary_dest} bus travel safety night buses day buses"
        ])
        
        # Scams and safety specific
        queries.extend([
            f"{primary_dest} tourist scams to avoid common tricks",
            f"{primary_dest} pickpocket areas safety warnings",
            f"{primary_dest} fake travel agents hotel booking scams"
        ])
        
        return queries[:15]  # Limit to prevent excessive API calls

    def _slugify(self, text: str) -> str:
        return "-".join("".join(c.lower() if c.isalnum() else " " for c in text).split())[:60]

    def _save_outputs(self, query: str, results: List[SearchResult], insights: List[Insight], markdown: str) -> None:
        out_dir = Path(self.settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = self._slugify(query)

        # Save raw search results
        with open(out_dir / f"{slug}.search.json", "w", encoding="utf-8") as f:
            json.dump([r.__dict__ for r in results], f, indent=2, ensure_ascii=False)

        # Save insights
        with open(out_dir / f"{slug}.insights.json", "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in insights], f, indent=2, ensure_ascii=False)

        # Save itinerary markdown
        with open(out_dir / f"{slug}.md", "w", encoding="utf-8") as f:
            f.write(markdown)

        self.logger.info(f"Saved outputs to {out_dir} with slug {slug}")