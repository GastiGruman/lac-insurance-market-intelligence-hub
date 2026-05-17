from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import requests


@dataclass(frozen=True)
class NewsConfig:
    configured: bool
    provider: str
    api_key: str | None = None
    status_message: str = "News module not configured."
    google_search_engine_id: str | None = None


def get_news_config() -> NewsConfig:
    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        return NewsConfig(
            configured=True,
            provider="newsapi",
            api_key=news_api_key,
            status_message="News configured with NewsAPI.",
        )

    bing_key = os.getenv("BING_SEARCH_API_KEY")
    if bing_key:
        return NewsConfig(
            configured=True,
            provider="bing",
            api_key=bing_key,
            status_message="News configured with Bing Search.",
        )

    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        return NewsConfig(
            configured=True,
            provider="serpapi",
            api_key=serpapi_key,
            status_message="News configured with SerpAPI.",
        )

    google_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    google_cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if google_key and google_cx:
        return NewsConfig(
            configured=True,
            provider="google",
            api_key=google_key,
            google_search_engine_id=google_cx,
            status_message="News configured with Google Custom Search.",
        )

    return NewsConfig(configured=False, provider="none")


def _safe_get(url: str, *, headers: dict | None = None, params: dict | None = None, timeout: int = 30) -> dict[str, Any]:
    response = requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def query_news_provider(config: NewsConfig, query: str, language: str = "es", limit: int = 10) -> list[dict]:
    if not config.configured:
        return []

    if config.provider == "newsapi":
        payload = _safe_get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": language,
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": config.api_key,
            },
        )
        articles = payload.get("articles", [])
        return [
            {
                "title": item.get("title"),
                "source": (item.get("source") or {}).get("name"),
                "date": item.get("publishedAt"),
                "link": item.get("url"),
                "summary": item.get("description") or item.get("content"),
                "raw_provider": "NewsAPI",
            }
            for item in articles[:limit]
        ]

    if config.provider == "bing":
        payload = _safe_get(
            "https://api.bing.microsoft.com/v7.0/news/search",
            headers={"Ocp-Apim-Subscription-Key": config.api_key or ""},
            params={
                "q": query,
                "mkt": "es-CO",
                "sortBy": "Date",
                "count": limit,
                "safeSearch": "Moderate",
            },
        )
        articles = payload.get("value", [])
        return [
            {
                "title": item.get("name"),
                "source": (item.get("provider") or [{}])[0].get("name"),
                "date": item.get("datePublished"),
                "link": item.get("url"),
                "summary": item.get("description"),
                "raw_provider": "Bing Search",
            }
            for item in articles[:limit]
        ]

    if config.provider == "serpapi":
        payload = _safe_get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_news",
                "q": query,
                "gl": "co",
                "hl": "es-419",
                "api_key": config.api_key,
            },
        )
        articles = payload.get("news_results", [])
        return [
            {
                "title": item.get("title"),
                "source": item.get("source"),
                "date": item.get("date"),
                "link": item.get("link"),
                "summary": item.get("snippet"),
                "raw_provider": "SerpAPI",
            }
            for item in articles[:limit]
        ]

    if config.provider == "google":
        payload = _safe_get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": config.api_key,
                "cx": config.google_search_engine_id,
                "q": query,
                "num": min(limit, 10),
                "safe": "active",
            },
        )
        articles = payload.get("items", [])
        return [
            {
                "title": item.get("title"),
                "source": item.get("displayLink"),
                "date": None,
                "link": item.get("link"),
                "summary": item.get("snippet"),
                "raw_provider": "Google Custom Search",
            }
            for item in articles[:limit]
        ]

    return []
