from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Literal, Dict, Any

from ddgs import DDGS
from tavily import TavilyClient
import httpx
from trafilatura import extract
from urllib.parse import urlparse

# New imports for caching
import os
import json
import hashlib

from src.utils.logger import get_logger
from src.utils.config import Settings


@dataclass
class SearchResult:
    source: str
    title: str
    url: str
    snippet: str
    content: str | None


class SearchTools:
    """Core search functionality for MCP Search Agent"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("search_mcp")
        self.tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None

    # --- Simple file cache helpers ---
    def _cache_key(self, query: str) -> str:
        base = f"{self.settings.search_provider}:{query}".encode("utf-8")
        return hashlib.sha1(base).hexdigest()

    def _cache_path(self, key: str) -> str:
        os.makedirs(self.settings.cache_dir, exist_ok=True)
        return os.path.join(self.settings.cache_dir, f"search_{key}.json")

    def _read_cache(self, query: str) -> List[SearchResult] | None:
        try:
            key = self._cache_key(query)
            path = self._cache_path(key)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [SearchResult(**item) for item in data]
        except Exception as e:
            self.logger.debug(f"Search cache read failed: {e}")
        return None

    def _write_cache(self, query: str, items: List[SearchResult]) -> None:
        try:
            key = self._cache_key(query)
            path = self._cache_path(key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([r.__dict__ for r in items], f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.debug(f"Search cache write failed: {e}")

    # --- Reality-first reranking ---
    def _score_result(self, r: SearchResult) -> float:
        """Give higher scores to real-world experience sources and posts about issues/scams."""
        score = 0.0
        try:
            domain = urlparse(r.url).netloc.lower()
            path = urlparse(r.url).path.lower()
        except Exception:
            domain = ""
            path = ""
        text = f"{r.title} {r.snippet}".lower()

        # Positive signals: forums, first-hand experiences, Q&A
        positives = [
            ("reddit.com", 5.0),
            ("tripadvisor.com", 3.5),  # esp. /ShowTopic forum threads
            ("travel.stackexchange.com", 4.0),
            ("/forum", 2.5),
            ("forum.", 2.0),
            ("medium.com", 1.5),
            ("wordpress", 1.5),
            ("blogspot", 1.2),
            ("blog", 1.0),
            ("quora.com", 1.0),
        ]
        for key, w in positives:
            if key in domain or key in path:
                score += w
        # Content hints
        if any(k in text for k in ["scam", "warning", "avoid", "safety", "pickpocket", "got scammed", "experience", "what went wrong"]):
            score += 1.0
        if any(k in text for k in ["tips", "hacks", "mistakes", "lessons"]):
            score += 0.6

        # Negative signals: affiliate-heavy or booking pages dominating SEO
        negatives = [
            ("booking.com", -2.5),
            ("agoda.com", -2.5),
            ("makemytrip", -2.0),
            ("trip.com", -2.0),
            ("expedia", -1.5),
            ("skyscanner", -1.2),
            ("kayak", -1.0),
            ("viator", -2.0),
            ("getyourguide", -2.0),
        ]
        for key, w in negatives:
            if key in domain:
                score += w

        # Slight boost for official advisories when relevant
        if any(k in domain for k in [".gov", "embassy", "consulate"]):
            score += 0.5
        return score

    def _rerank_reality_first(self, items: List[SearchResult]) -> List[SearchResult]:
        return sorted(items, key=self._score_result, reverse=True)

    def search(self, query: str) -> List[SearchResult]:
        """Main search entry point - combines DuckDuckGo and Tavily results"""
        provider = self.settings.search_provider
        self.logger.info(f"Searching with provider: {provider}")

        # Return cached result if available
        cached = self._read_cache(query)
        if cached is not None:
            self.logger.info("Using cached search results")
            return cached

        results: List[SearchResult] = []

        if provider in ("duckduckgo", "hybrid"):
            results += self._search_duckduckgo(query)
        if provider in ("tavily", "hybrid") and self.tavily is not None:
            results += self._search_tavily(query)
        elif provider == "tavily" and self.tavily is None:
            self.logger.warning("Tavily selected but TAVILY_API_KEY not set. Falling back to DuckDuckGo.")
            results += self._search_duckduckgo(query)

        # Deduplicate by URL
        seen = set()
        deduped: List[SearchResult] = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                deduped.append(r)

        # Reality-first rerank before fetching content
        reranked = self._rerank_reality_first(deduped)

        # Fetch contents for top results
        final = self._fetch_contents(reranked[: self.settings.max_results])
        # Write cache
        self._write_cache(query, final)
        return final

    def _search_duckduckgo(self, query: str) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        out: List[SearchResult] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, safesearch="Off", max_results=self.settings.max_results):
                    out.append(
                        SearchResult(
                            source="duckduckgo",
                            title=r.get("title", ""),
                            url=r.get("href", ""),
                            snippet=r.get("body", ""),
                            content=None,
                        )
                    )
        except Exception as e:
            self.logger.debug(f"DuckDuckGo search failed: {e}")
        self.logger.info(f"DuckDuckGo returned {len(out)} results")
        return out

    def _compress_query(self, query: str, limit: int = 380) -> str:
        """Compress query to meet Tavily's length limits while preserving meaning."""
        q = " ".join(query.split())  # collapse whitespace
        if len(q) <= limit:
            return q
        # Heuristic: keep first N words
        words = q.split(" ")
        q2 = " ".join(words[:80])  # cap to ~80 words
        if len(q2) > limit:
            q2 = q2[:limit]
        return q2

    def _search_tavily(self, query: str) -> List[SearchResult]:
        """Search using Tavily with graceful degradation when query is too long."""
        out: List[SearchResult] = []
        if not self.tavily:
            return out
        q = self._compress_query(query, limit=380)
        try:
            r = self.tavily.search(query=q, search_depth="advanced", max_results=self.settings.max_results)
        except Exception as e:
            # Try a more aggressive compression, then fall back to DuckDuckGo
            self.logger.warning(f"Tavily search failed on first attempt: {e}. Retrying with stricter compression.")
            try:
                q2 = self._compress_query(query, limit=350)
                r = self.tavily.search(query=q2, search_depth="advanced", max_results=self.settings.max_results)
            except Exception as e2:
                self.logger.warning(f"Tavily search failed again: {e2}. Falling back to DuckDuckGo.")
                return self._search_duckduckgo(query)
        for item in r.get("results", []):
            out.append(
                SearchResult(
                    source="tavily",
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    content=None,
                )
            )
        self.logger.info(f"Tavily returned {len(out)} results")
        return out

    def _fetch_contents(self, items: List[SearchResult]) -> List[SearchResult]:
        """Fetch full content for search results"""
        client = httpx.Client(timeout=self.settings.request_timeout, follow_redirects=True, headers={"User-Agent": "RouteWiseBot/0.1"})
        out: List[SearchResult] = []
        for it in items:
            text = None
            try:
                resp = client.get(it.url)
                if resp.status_code == 200:
                    text = extract(resp.text) or None
            except Exception as e:
                self.logger.debug(f"Failed to fetch {it.url}: {e}")
            out.append(SearchResult(**{**it.__dict__, "content": text}))
            time.sleep(0.2)  # be polite
        client.close()
        return out