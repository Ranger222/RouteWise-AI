from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Literal, Dict, Any

from ddgs import DDGS
from tavily import TavilyClient
import httpx
from trafilatura import extract

from src.utils.logger import get_logger
from src.utils.config import Settings


@dataclass
class SearchResult:
    source: str
    title: str
    url: str
    snippet: str
    content: str | None


class SearchAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("search")
        self.tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None

    def search(self, query: str) -> List[SearchResult]:
        provider = self.settings.search_provider
        self.logger.info(f"Searching with provider: {provider}")
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

        # Fetch contents for top results
        return self._fetch_contents(deduped[: self.settings.max_results])

    def _search_duckduckgo(self, query: str) -> List[SearchResult]:
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

    def _search_tavily(self, query: str) -> List[SearchResult]:
        out: List[SearchResult] = []
        if not self.tavily:
            return out
        r = self.tavily.search(query=query, search_depth="advanced", max_results=self.settings.max_results)
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