from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from src.news_sources import NewsConfig, query_news_provider


CACHE_DIR = Path("outputs/news_cache")
CACHE_TTL_HOURS = 12


def sanitize_cache_key(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")[:60]
    return f"{slug}_{digest}" if slug else digest


def build_company_news_query(company: str, country: str = "Colombia") -> str:
    return (
        f'"{company}" seguros OR aseguradora OR reaseguro OR Fasecolda OR Superfinanciera '
        f'{country}'
    )


def build_market_news_query(country: str = "Colombia") -> str:
    return (
        f'seguros aseguradoras reaseguro Fasecolda Superfinanciera regulación mercado {country}'
    )


def build_relevance(text: str, scope: str) -> str:
    normalized = str(text or "").lower()
    signals = []
    if any(token in normalized for token in ["reaseguro", "reinsurance", "catástrofe", "catastrofe"]):
        signals.append("possible reinsurance angle")
    if any(token in normalized for token in ["regulación", "regulacion", "superfinanciera", "decreto", "circular"]):
        signals.append("regulatory monitoring")
    if any(token in normalized for token in ["calificación", "calificacion", "rating", "fitch", "s&p", "moody"]):
        signals.append("rating or credit watch")
    if any(token in normalized for token in ["resultados", "utilidad", "primas", "siniestros", "crecimiento"]):
        signals.append("market performance context")
    if any(token in normalized for token in ["ia", "inteligencia artificial", "ai insurance", "insurtech"]):
        signals.append("AI or technology market signal")

    if not signals:
        signals.append("general market context")

    return f"{scope}: " + "; ".join(dict.fromkeys(signals))


def normalize_news_items(items: list[dict], query: str, scope: str) -> list[dict]:
    normalized = []
    seen_links = set()
    for item in items:
        link = item.get("link")
        title = item.get("title")
        if not title or not link or link in seen_links:
            continue
        seen_links.add(link)
        combined_text = f"{title} {item.get('summary') or ''}"
        normalized.append(
            {
                "title": title,
                "source": item.get("source") or item.get("raw_provider") or "Unknown source",
                "date": item.get("date") or "Date not available",
                "link": link,
                "summary": item.get("summary") or "Summary not available from provider.",
                "relevance": build_relevance(combined_text, scope),
                "query": query,
                "retrieved_at": datetime.now().isoformat(timespec="seconds"),
                "provider": item.get("raw_provider") or "Unknown provider",
            }
        )
    return normalized


def _cache_path(cache_key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{cache_key}.json"


def _read_cache(cache_key: str) -> list[dict] | None:
    path = _cache_path(cache_key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(payload.get("cached_at"))
        if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
            return None
        return payload.get("items", [])
    except Exception:
        return None


def _write_cache(cache_key: str, items: list[dict]) -> None:
    path = _cache_path(cache_key)
    payload = {
        "cached_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_news(
    config: NewsConfig,
    query: str,
    scope: str,
    limit: int = 10,
    refresh: bool = False,
) -> dict:
    if not config.configured:
        return {
            "configured": False,
            "items": [],
            "message": "News module not configured.",
            "cached": False,
        }

    cache_key = sanitize_cache_key(f"{config.provider}:{query}:{limit}")
    if not refresh:
        cached = _read_cache(cache_key)
        if cached is not None:
            return {
                "configured": True,
                "items": cached,
                "message": "Loaded from local news cache.",
                "cached": True,
            }

    try:
        raw_items = query_news_provider(config, query=query, limit=limit)
        items = normalize_news_items(raw_items, query=query, scope=scope)
        _write_cache(cache_key, items)
        return {
            "configured": True,
            "items": items,
            "message": "News retrieved from configured provider.",
            "cached": False,
        }
    except Exception as exc:
        cached = _read_cache(cache_key)
        if cached is not None:
            return {
                "configured": True,
                "items": cached,
                "message": f"Provider unavailable; loaded cached results. Error: {exc}",
                "cached": True,
            }
        return {
            "configured": True,
            "items": [],
            "message": f"News provider unavailable: {exc}",
            "cached": False,
        }


def news_items_to_dataframe(items: list[dict]) -> pd.DataFrame:
    cols = ["title", "source", "date", "link", "summary", "relevance", "provider", "retrieved_at"]
    if not items:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(items)[cols]
