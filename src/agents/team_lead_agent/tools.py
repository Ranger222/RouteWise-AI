"""Team Lead orchestration tools for MCP workflow"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

from src.utils.logger import get_logger
from src.utils.config import Settings
from src.agents.search_agent.server import SearchMCPServer
from src.agents.reality_miner_agent.server import RealityMinerMCPServer  
from src.agents.itinerary_agent.server import ItineraryMCPServer


class TeamLeadTools:
    """Orchestration tools for coordinating all MCP agents"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("team_lead_mcp")
        
        # Initialize MCP servers
        self.search_server = SearchMCPServer(settings)
        self.miner_server = RealityMinerMCPServer(settings)
        self.itinerary_server = ItineraryMCPServer(settings)
    
    def orchestrate_workflow(self, query: str, save: bool = True) -> str:
        """Main workflow orchestration: Search → Mine → Synthesize"""
        self.logger.info("Starting MCP workflow: Multi-Search → Mine → Synthesize")
        
        # Multi-query search strategy for comprehensive data collection
        search_queries = self._generate_search_queries(query)
        if getattr(self.settings, "fast_mode", False):
            # Aggressively cap in fast mode
            search_queries = search_queries[:5]
            self.logger.info(f"FAST_MODE active: limiting search queries to {len(search_queries)}")
        all_results = []
        
        for search_query in search_queries:
            self.logger.info(f"Searching via MCP: {search_query}")
            results = self.search_server.search_route(search_query)
            all_results.extend(results)
        
        # Deduplicate by URL across all searches
        seen = set()
        deduped = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                deduped.append(r)
        
        # In fast mode, keep fewer docs to speed up LLM calls
        docs: List[Dict[str, Any]] = [r.__dict__ for r in deduped if (r.content or r.snippet)]
        if getattr(self.settings, "fast_mode", False):
            docs = docs[:12]
            self.logger.info(f"FAST_MODE active: limiting docs to {len(docs)} for mining")
        else:
            self.logger.info(f"Total unique documents collected: {len(docs)}")

        # Extract insights via Reality Miner MCP
        insights = self.miner_server.extract(query, docs)
        
        # In fast mode, keep fewer insights into itinerary to shorten prompt
        if getattr(self.settings, "fast_mode", False):
            insights = insights[:16]
            self.logger.info(f"FAST_MODE active: limiting insights passed to itinerary to {len(insights)}")
        
        # Generate itinerary via Itinerary MCP
        itinerary = self.itinerary_server.build_itinerary(query, insights)

        # Skip saving artifacts in fast mode to reduce I/O
        if save and not getattr(self.settings, "fast_mode", False):
            self._save_outputs(query, deduped, insights, itinerary.markdown)
        
        return itinerary.markdown
    
    def _generate_search_queries(self, query: str) -> List[str]:
        """Generate comprehensive search queries from user input"""
        # Extract primary destination (simple heuristic)
        words = query.lower().split()
        destinations = []
        for word in words:
            if word in ["delhi", "jaipur", "mumbai", "goa", "agra", "rajasthan", "india"]:
                destinations.append(word.capitalize())
        
        primary_dest = destinations[0] if destinations else "India"
        
        queries = []
        # Base travel queries
        queries.extend([
            f"{query} complete guide travel tips",
            f"{primary_dest} travel guide budget tips safety",
            f"{primary_dest} best time to visit weather season",
            f"{primary_dest} tourist attractions must visit places"
        ])
        
        # Transport and booking queries
        queries.extend([
            f"{primary_dest} train booking IRCTC how to book tickets",
            f"{primary_dest} bus booking RedBus state transport",
            f"{primary_dest} local transport metro auto rickshaw Uber Ola",
            f"{primary_dest} airport to city center transport options"
        ])
        
        # Accommodation queries
        queries.extend([
            f"{primary_dest} budget hotels hostels accommodation near railway station",
            f"{primary_dest} safe areas to stay neighborhoods for tourists",
            f"{primary_dest} accommodation booking tips avoid scams",
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
    
    def _save_outputs(self, query: str, search_results, insights, markdown: str):
        """Save workflow outputs to files"""
        # Create safe filename
        safe_query = "".join(c if c.isalnum() or c in "-_" else "-" for c in query.lower()[:50])
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save search results
        search_file = output_dir / f"{safe_query}.search.json"
        with open(search_file, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in search_results], f, indent=2, ensure_ascii=False)
        
        # Save insights
        insights_file = output_dir / f"{safe_query}.insights.json"
        with open(insights_file, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in insights], f, indent=2, ensure_ascii=False)
        
        # Save final markdown
        markdown_file = output_dir / f"{safe_query}.itinerary.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        self.logger.info(f"Outputs saved: {search_file.name}, {insights_file.name}, {markdown_file.name}")