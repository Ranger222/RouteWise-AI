"""Team Lead orchestration tools for MCP workflow"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import time
import os

from src.utils.logger import get_logger
from src.utils.config import Settings
from src.agents.search_agent.server import SearchMCPServer
from src.agents.reality_miner_agent.server import RealityMinerMCPServer  
from src.agents.itinerary_agent.server import ItineraryMCPServer
from mistralai import Mistral

# New MCP agent servers
from src.agents.flight_agent.server import FlightMCPServer
from src.agents.visa_agent.server import VisaMCPServer
from src.agents.checklist_agent.server import ChecklistMCPServer
from src.agents.budget_agent.server import BudgetMCPServer


class TeamLeadTools:
    """Orchestration tools for coordinating all MCP agents"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("team_lead_mcp")
        
        # Initialize MCP servers
        self.search_server = SearchMCPServer(settings)
        self.miner_server = RealityMinerMCPServer(settings)
        self.itinerary_server = ItineraryMCPServer(settings)
        # Initialize new specialized MCP servers
        self.flight_server = FlightMCPServer(settings)
        self.visa_server = VisaMCPServer(settings)
        self.checklist_server = ChecklistMCPServer(settings)
        self.budget_server = BudgetMCPServer(settings)
        # Mistral client for parameter extraction
        self.mistral = Mistral(api_key=settings.mistral_api_key)

    # --- Helpers ---
    def _save_outputs(self, query: str, results: List[Any], insights: List[Any], itinerary_md: str):
        out_dir = Path(self.settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        key = "artifact"
        (out_dir / f"{key}.search.json").write_text(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / f"{key}.insights.json").write_text(json.dumps([asdict(i) for i in insights], indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / f"{key}.md").write_text(itinerary_md, encoding="utf-8")

    def _generate_search_queries(self, query: str) -> List[str]:
        """Generate context-aware, reality-focused search queries via LLM (no hardcoding).
        Falls back to a reasonable static set if LLM generation fails.
        """
        q = (query or "").strip()
        # LLM-directed query planner prompt
        system = (
            "You are an expert travel search planner. Given a user's intent, generate 10-15 focused web "
            "search queries that emphasize REAL traveller experiences, seasonal issues (like Diwali festivals), "
            "ground realities (scams, delays, surge pricing), and forum discussions. \n"
            "Guidelines: \n"
            "- Prioritize sources like reddit, tripadvisor forums, travel.stackexchange, local news, and blogs. \n"
            "- Include seasonal/festival-specific angles when applicable (e.g., Diwali/Christmas/Holi causing surge pricing, traffic, delays). \n"
            "- Mix general queries and site-scoped ones (e.g., site:reddit.com, site:tripadvisor.com/ShowTopic). \n"
            "- Focus on: transport safety, bus/train/flight price surges, crowd control, closures, scams, and first-hand experiences. \n"
            "- Return STRICT JSON array of strings (no extra text)."
        )
        user = (
            f"User Query: {q}\n\n"
            "Return a JSON array of 10-15 search queries tailored to this intent."
        )

        queries: List[str] = []
        try:
            resp = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
            )
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    # keep strings only
                    queries = [str(x).strip() for x in data if isinstance(x, (str, int, float))]
            except Exception:
                # Best-effort recovery
                start = content.find("[")
                end = content.rfind("]")
                payload = content[start:end+1] if start != -1 and end != -1 else "[]"
                try:
                    from json_repair import repair_json
                    data = json.loads(repair_json(payload))
                    if isinstance(data, list):
                        queries = [str(x).strip() for x in data if isinstance(x, (str, int, float))]
                except Exception:
                    queries = []
        except Exception as e:
            self.logger.warning(f"LLM query planning failed: {e}")
            queries = []

        if not queries:
            # Fallback to legacy heuristic set to avoid total failure
            base = [
                q,
                f"{q} reddit experiences tips",
                f"{q} site:reddit.com travel advice problems",
                f"{q} site:tripadvisor.com/ShowTopic forum issues scams",
                f"{q} site:travel.stackexchange.com safety visas transport",
                f"{q} blog personal experience what to avoid",
            ]
            reality = [
                f"{q} common scams to avoid taxi rickshaw overcharge",
                f"{q} safety at night solo women experiences",
                f"{q} pickpocket areas crowded warnings",
                f"{q} local transport hacks train bus metro delays",
                f"{q} bad experiences what went wrong lessons learned",
                f"{q} festival crowd traffic surge pricing",
            ]
            practicals = [
                f"{q} airport to city transport real cost avoid scams",
                f"{q} neighborhoods to avoid where to stay reddit",
                f"{q} hostel vs hotel area to stay budget",
                f"{q} best time to visit avoid crowds heat rain",
                f"{q} food hygiene street food safety upset stomach",
            ]
            queries = base + reality + practicals
        
        # Cap in FAST_MODE
        if getattr(self.settings, "fast_mode", False):
            queries = queries[:4]
        else:
            queries = queries[:15]
        
        return queries

    def _expand_queries_from_results(self, original_query: str, results: List[Any]) -> List[str]:
        """Generate deeper, nested queries based on early results (titles/snippets)."""
        # Build compact context from top results
        items = []
        for r in results[:6]:
            try:
                title = getattr(r, 'title', '') or r.get('title', '')  # type: ignore[attr-defined]
                snippet = getattr(r, 'snippet', '') or r.get('snippet', '')  # type: ignore[attr-defined]
                url = getattr(r, 'url', '') or r.get('url', '')  # type: ignore[attr-defined]
                if title or snippet:
                    items.append(f"TITLE: {title}\nSNIPPET: {snippet}\nURL: {url}")
            except Exception:
                continue
        context = "\n\n".join(items)[:4000]
        if not context:
            return []

        system = (
            "You are a search refiner. Given a user intent and some early search results, propose 5-8 follow-up "
            "queries that go DEEPER into reality-first angles: seasonal problems (e.g., Diwali travel issues), price surges, "
            "route-specific challenges (origin/destination), scams, on-ground logistics, and first-hand reports. "
            "Favor site-scoped queries (reddit, tripadvisor forums, travel.stackexchange) and local news/blogs. "
            "Return STRICT JSON array of strings only."
        )
        user = (
            f"User Query: {original_query}\n\nEarly Results Context:\n{context}\n\n"
            "Return a JSON array of 5-8 refined queries."
        )
        followups: List[str] = []
        try:
            resp = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
            )
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    followups = [str(x).strip() for x in data if isinstance(x, (str, int, float))]
            except Exception:
                start = content.find("[")
                end = content.rfind("]")
                payload = content[start:end+1] if start != -1 and end != -1 else "[]"
                try:
                    from json_repair import repair_json
                    data = json.loads(repair_json(payload))
                    if isinstance(data, list):
                        followups = [str(x).strip() for x in data if isinstance(x, (str, int, float))]
                except Exception:
                    followups = []
        except Exception as e:
            self.logger.debug(f"Follow-up query refinement failed: {e}")
            followups = []

        # Cap number of follow-ups
        return (followups or [])[:6]

    def _extract_trip_params(self, query: str) -> Dict[str, Any]:
        """Use Mistral to extract trip parameters from the user's query.
        Returns fields like origin_city, destination_city, depart_date, return_date, is_first_time, duration_days.
        """
        system = (
            "You are a travel intent parser. Return STRICT JSON with fields: "
            "origin_city (string|nullable), destination_city (string|nullable), depart_date (YYYY-MM-DD|nullable), "
            "return_date (YYYY-MM-DD|nullable), duration_days (int|nullable), is_first_time (bool), notes (string). "
            "Infer missing fields conservatively from the text; don't invent cities. If the text mentions Gurugram/Noida/Delhi NCR, map origin_city to Delhi."
        )
        user = f"User Query: {query}"
        try:
            resp = self.mistral.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
            )
            content = ""
            try:
                content = resp.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                content = getattr(resp, "output_text", "") or str(resp)
            data: Dict[str, Any]
            try:
                data = json.loads(content)
            except Exception:
                # Best-effort JSON recovery
                start = content.find("{")
                end = content.rfind("}")
                payload = content[start:end+1] if start != -1 and end != -1 else "{}"
                try:
                    from json_repair import repair_json
                    data = json.loads(repair_json(payload))
                except Exception:
                    data = {}
        except Exception as e:
            self.logger.warning(f"Param extraction failed: {e}")
            data = {}
        # Normalize
        if data.get("origin_city"):
            city = data["origin_city"].lower()
            if any(x in city for x in ["gurugram", "gurgaon", "noida", "delhi"]):
                data["origin_city"] = "Delhi"
        data.setdefault("is_first_time", False)
        return data

    def _is_domestic_trip(self, params: Dict[str, Any]) -> bool:
        """Check if this is a domestic trip within India based on extracted parameters."""
        origin = str(params.get("origin_city", "")).lower()
        dest = str(params.get("destination_city", "")).lower()
        
        # Common Indian cities/regions
        indian_places = [
            "delhi", "mumbai", "bangalore", "kolkata", "chennai", "hyderabad", "pune", "ahmedabad",
            "jaipur", "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam",
            "patna", "vadodara", "ludhiana", "agra", "nashik", "faridabad", "meerut", "rajkot",
            "kalyan", "vasai", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar",
            "navi mumbai", "allahabad", "howrah", "ranchi", "gwalior", "jabalpur", "coimbatore",
            "vijayawada", "jodhpur", "madurai", "raipur", "kota", "guwahati", "chandigarh",
            "solapur", "hubli", "mysore", "tiruchirappalli", "bareilly", "moradabad", "gurgaon",
            "gurugram", "noida", "ghaziabad", "aligarh", "jalandhar", "bhubaneswar", "salem",
            "warangal", "mira", "bhiwandi", "thiruvananthapuram", "bhavnagar", "dehradun", "durgapur",
            "kerala", "goa", "rajasthan", "punjab", "haryana", "uttar pradesh", "bihar", "odisha",
            "west bengal", "tamil nadu", "karnataka", "andhra pradesh", "telangana", "madhya pradesh",
            "gujarat", "maharashtra", "himachal pradesh", "uttarakhand", "jharkhand", "chhattisgarh"
        ]
        
        # Check if both origin and destination contain Indian place names
        origin_in_india = any(place in origin for place in indian_places)
        dest_in_india = any(place in dest for place in indian_places)
        
        # Additional heuristics: if query mentions "domestic", "within India", etc.
        notes = str(params.get("notes", "")).lower()
        explicit_domestic = any(phrase in notes for phrase in ["domestic", "within india", "inside india"])
        
        return (origin_in_india and dest_in_india) or explicit_domestic

    def orchestrate_workflow(self, query: str, save: bool = True) -> str:
        """Main workflow orchestration: Search → Mine → Specialized → Synthesize"""
        self.logger.info("Starting MCP workflow: Multi-Search → Mine → Specialized → Synthesize")
        # Global time budget to ensure we return before the frontend aborts (~120s)
        # Default to 90s unless overridden via env PLANNER_TIME_BUDGET (min 45, max 100)
        start_ts = time.perf_counter()
        try:
            time_budget = int(os.getenv("PLANNER_TIME_BUDGET", "90"))
        except Exception:
            time_budget = 90
        time_budget = max(45, min(time_budget, 100))

        def remaining() -> float:
            return time_budget - (time.perf_counter() - start_ts)
        # Trip parameter extraction (early for route detection)
        params = self._extract_trip_params(query)
        is_domestic = self._is_domestic_trip(params)
        self.logger.info(f"Route detected: {'Domestic' if is_domestic else 'International'} trip")
        
        # Derive trip duration in days if possible for gating budget/itinerary sections
        duration_days = None
        try:
            dd = params.get("duration_days")
            if isinstance(dd, int):
                duration_days = dd
        except Exception:
            duration_days = None
        if (duration_days is None) and params.get("depart_date") and params.get("return_date"):
            try:
                dep = datetime.fromisoformat(str(params["depart_date"]))
                ret = datetime.fromisoformat(str(params["return_date"]))
                delta = (ret - dep).days
                duration_days = max(delta, 0) + 1 if delta >= 0 else None
            except Exception:
                duration_days = None

        # Multi-query search strategy for comprehensive data collection (LLM-planned)
        search_queries = self._generate_search_queries(query)
        if getattr(self.settings, "fast_mode", False):
            # Aggressively cap in fast mode
            search_queries = search_queries[:2]
            self.logger.info(f"FAST_MODE active: limiting search queries to {len(search_queries)}")
        elif remaining() < 60:
            # Time-pressure: trim planned searches
            original_len = len(search_queries)
            search_queries = search_queries[:4]
            self.logger.info(f"Time budget: limiting search queries to {len(search_queries)} (from {original_len})")
        all_results = []
        
        for search_query in search_queries:
            self.logger.info(f"Searching via MCP: {search_query}")
            results = self.search_server.search_route(search_query)
            all_results.extend(results)
            if remaining() < 35:
                self.logger.info("Time budget nearly exhausted after search; breaking early")
                break
        # Optional nested refinement pass (deeper queries) when not in FAST_MODE
        if (not getattr(self.settings, "fast_mode", False)) and remaining() >= 50:
            try:
                followups = self._expand_queries_from_results(query, all_results)
                if followups:
                    self.logger.info(f"Refinement: executing {len(followups)} follow-up queries")
                    for fq in followups:
                        results2 = self.search_server.search_route(fq)
                        all_results.extend(results2)
                        if remaining() < 38:
                            self.logger.info("Time budget low during refinement; stopping follow-ups")
                            break
            except Exception as e:
                self.logger.debug(f"Refinement pass skipped due to error: {e}")
        
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
            docs = docs[:6]
            self.logger.info(f"FAST_MODE active: limiting docs to {len(docs)} for mining")
        else:
            self.logger.info(f"Total unique documents collected: {len(docs)}")
        
        # Time-pressure trimming of docs
        if remaining() < 25:
            docs = docs[:2]
            self.logger.info("Time budget: limiting docs to 2 for mining")
        elif remaining() < 40:
            docs = docs[:4]
            self.logger.info("Time budget: limiting docs to 4 for mining")

        # Extract insights via Reality Miner MCP
        if remaining() < 22:
            self.logger.info("Time budget: skipping mining; proceeding with minimal insights")
            insights = []
        else:
            insights = self.miner_server.extract(query, docs)
        
        # In fast mode, keep fewer insights into itinerary to shorten prompt
        if getattr(self.settings, "fast_mode", False):
            insights = insights[:16]
            self.logger.info(f"FAST_MODE active: limiting insights passed to itinerary to {len(insights)}")
        
        # Generate itinerary via Itinerary MCP
        if remaining() < 14:
            self.logger.info("Time budget: using quick inline itinerary fallback")
            header_bits = []
            if params.get("origin_city") and params.get("destination_city"):
                header_bits.append(f"Your Trip: {params['origin_city']} → {params['destination_city']}")
            quick = ("\n".join(header_bits) + ("\n\n" if header_bits else "")) + (
                "Quick Plan (compact):\n"
                "- Start with 2–3 must‑do highlights and one standout food spot.\n"
                "- Getting around: use metro/bus; rideshare for late nights; keep small cash.\n"
                "- Heads‑up: verify timings/prices on official sites; keep an eye on scams around stations.\n"
                "- Next steps: tell me dates, trip length, budget vibe — I’ll flesh out a day‑by‑day in seconds."
            )
            itinerary = type("Itin", (), {})()
            itinerary.markdown = quick
        else:
            itinerary = self.itinerary_server.build_itinerary(query, insights)

        # Build a condensed "Reality Check" section from mined insights (scams, warnings, challenges)
        reality_md = ""
        try:
            bullets: List[str] = []
            for i in insights[:20]:
                itype = (getattr(i, 'type', None) or (i.get('type') if isinstance(i, dict) else '') or '').lower()
                if any(k in itype for k in ["warning", "scam", "caution", "issue", "problem", "hack", "tip", "safety"]):
                    summary = getattr(i, 'summary', None) or (i.get('summary') if isinstance(i, dict) else '') or ''
                    url = getattr(i, 'source_url', None) or (i.get('source_url') if isinstance(i, dict) else '') or ''
                    if summary:
                        if url:
                            bullets.append(f"- {summary} — source: {url}")
                        else:
                            bullets.append(f"- {summary}")
                if len(bullets) >= 8:
                    break
            if bullets:
                reality_md = "\n".join(bullets)
        except Exception as e:
            self.logger.debug(f"Reality Check assembly failed: {e}")

        # Specialized agents - conditional based on route type and explicit user intent
        flights_md = ""
        visa_md = ""
        checklist_md = ""
        budget_md = ""
        wants_flights = any(w in (query or "").lower() for w in ["flight", "flights", "air", "plane"])  # explicit flight ask
        if wants_flights and remaining() >= 20:
            try:
                flights_md = self.flight_server.suggest_flights(params)
            except Exception as e:
                self.logger.warning(f"Flight agent failed: {e}")
                flights_md = "- Flight suggestions unavailable right now. Use Google Flights/Skyscanner to compare prices."

        # Include visa only for international trips AND when the user asks about visa/documents
        wants_visa = (not is_domestic) and any(w in (query or "").lower() for w in ["visa", "passport", "documents", "immigration"])
        if wants_visa and remaining() >= 18:
            try:
                visa_md = self.visa_server.synthesize_guidance(params)
            except Exception as e:
                self.logger.warning(f"Visa agent failed: {e}")
                visa_md = "- Visa guidance unavailable. Verify requirements on the official embassy site."

        # Checklist - only include if first-time or explicitly asked
        wants_checklist = bool(params.get("is_first_time")) or any(w in (query or "").lower() for w in ["checklist", "packing", "pack", "what to bring"])
        if wants_checklist and remaining() >= 16:
            try:
                checklist_params = params.copy()
                checklist_params["is_domestic"] = is_domestic
                checklist_md = self.checklist_server.build_checklist(checklist_params)
            except Exception as e:
                self.logger.warning(f"Checklist agent failed: {e}")
                if is_domestic:
                    checklist_md = "- Valid ID (Aadhaar/PAN/DL); phone charger; local transport apps (Ola/Uber); small cash."
                else:
                    checklist_md = "- Checklist unavailable. Pack essentials: passport, visa, cards, adapter, meds, copies of documents."
        else:
            checklist_md = ""

        # Budget estimation (optional; include only if asked or duration is known)
        wants_budget = (isinstance(duration_days, int) and duration_days > 0) or any(k in (query or "").lower() for k in ["budget", "cost", "price", "expenses", "how much", "per day", "per-day"])
        if wants_budget and remaining() >= 18:
            try:
                # Pass domestic flag and derived duration to budget agent
                budget_params = params.copy()
                budget_params["is_domestic"] = is_domestic
                budget_params["duration_days"] = duration_days
                budget_md = self.budget_server.estimate_budget(budget_params)
            except Exception as e:
                self.logger.warning(f"Budget agent failed: {e}")
                if is_domestic:
                    budget_md = "- Budget: ₹1,500-₹3,500/day; Midrange: ₹4,000-₹7,500/day depending on city and accommodation."
                else:
                    budget_md = "- Budget estimate unavailable. Typical budget: $120–$220/day depending on stay and activities."
        else:
            budget_md = ""

        # Assemble final response - conditionally include sections
        header_bits = []
        if params.get("origin_city") and params.get("destination_city"):
            header_bits.append(f"Your Trip: {params['origin_city']} → {params['destination_city']}")
        dates_line = None
        if params.get("depart_date") and params.get("return_date"):
            dates_line = f"Dates: {params['depart_date']} → {params['return_date']}"
        if dates_line:
            header_bits.append(dates_line)
        if params.get("is_first_time") and not is_domestic:
            header_bits.append("First international trip — I'll make it step-by-step and confidence-boosting.")
        header = "\n".join(header_bits) if header_bits else ""

        # Build sections list based on route type (Reality first)
        sections = []
        if reality_md.strip():
            sections.append(f"Reality Check (from real traveller posts)\n{reality_md}")
        if flights_md.strip():
            sections.append(f"Flights\n{flights_md}")
        # Only include visa section when requested
        if visa_md.strip():
            sections.append(f"Documents & Visa\n{visa_md}")
        # Adjust checklist title for domestic vs international
        if checklist_md.strip():
            checklist_title = "Travel Checklist" if is_domestic else "Packing & First‑Time Checklist"
            sections.append(f"{checklist_title}\n{checklist_md}")
        if budget_md.strip():
            sections.append(f"Budget Overview\n{budget_md}")
        if itinerary.markdown.strip():
            sections.append(itinerary.markdown)

        final = "\n\n".join(([header] if header else []) + sections)

        # Skip saving artifacts in fast mode to reduce I/O
        if save and not getattr(self.settings, "fast_mode", False) and remaining() >= 12:
            self._save_outputs(query, deduped, insights, final)
        
        return final

    def _generate_search_queries_alt(self, query: str) -> List[str]:
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