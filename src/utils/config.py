import os
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv


@dataclass
class Settings:
    gemini_api_key: str
    mistral_api_key: str
    tavily_api_key: str | None
    search_provider: Literal["duckduckgo", "tavily", "hybrid"]
    max_results: int
    request_timeout: int
    output_dir: str
    cache_dir: str
    fast_mode: bool


def load_settings() -> Settings:
    load_dotenv()
    gemini = os.getenv("GEMINI_API_KEY", "")
    mistral = os.getenv("MISTRAL_API_KEY", "")
    tavily = os.getenv("TAVILY_API_KEY")
    provider = os.getenv("SEARCH_PROVIDER", "hybrid").lower()

    # Lower conservative defaults; .env can increase if needed
    max_results = int(os.getenv("MAX_RESULTS", "5"))
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "12"))
    output_dir = os.getenv("OUTPUT_DIR", "src/data/examples")
    cache_dir = os.getenv("CACHE_DIR", "src/data/cache")
    fast_mode = os.getenv("FAST_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}

    if provider not in {"duckduckgo", "tavily", "hybrid"}:
        provider = "hybrid"

    if not gemini:
        raise RuntimeError("GEMINI_API_KEY is required. Set it in .env")
    if not mistral:
        raise RuntimeError("MISTRAL_API_KEY is required. Set it in .env")

    return Settings(
        gemini_api_key=gemini,
        mistral_api_key=mistral,
        tavily_api_key=tavily,
        search_provider=provider,  # type: ignore
        max_results=max_results,
        request_timeout=request_timeout,
        output_dir=output_dir,
        cache_dir=cache_dir,
        fast_mode=fast_mode,
    )