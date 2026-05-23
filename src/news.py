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
CURATED_NEWS_PATH = Path("data/external/company_news_curated.csv")
KEY_PEOPLE_TEMPLATE_PATH = Path("data/external/company_key_people_template.csv")
ENABLE_LIVE_NEWS = False

NEWS_REQUIRED_COLUMNS = [
    "company_name",
    "company_name_norm",
    "country",
    "title",
    "date",
    "source",
    "url",
    "summary",
    "broker_relevance",
    "relevance_category",
    "relevance_score",
    "is_verified",
    "notes",
]

NEWS_CATEGORIES = [
    "Strategy",
    "Financial Results",
    "Regulation",
    "Claims / Catastrophe",
    "Product / Distribution",
    "M&A / Partnerships",
    "Technology / AI",
    "Leadership",
    "Reinsurance / Capital",
    "Other",
]


def sanitize_cache_key(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")[:60]
    return f"{slug}_{digest}" if slug else digest


def normalize_text(value) -> str:
    text = str(value or "").strip().upper()
    replacements = {
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ñ": "N",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return " ".join(text.split())


def _ensure_news_columns(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy() if df is not None else pd.DataFrame()
    for column in NEWS_REQUIRED_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA
    data = data[NEWS_REQUIRED_COLUMNS].copy()
    data["company_name"] = data["company_name"].fillna("").astype(str).str.strip()
    data["company_name_norm"] = data["company_name_norm"].fillna(data["company_name"]).map(normalize_text)
    data["country"] = data["country"].fillna("").astype(str).str.strip().str.upper()
    data["title"] = data["title"].fillna("").astype(str).str.strip()
    data["source"] = data["source"].fillna("Source not available").astype(str).str.strip()
    data["url"] = data["url"].fillna("").astype(str).str.strip()
    data["summary"] = data["summary"].fillna("Summary not available.").astype(str).str.strip()
    data["broker_relevance"] = data["broker_relevance"].fillna("Review relevance before use.").astype(str).str.strip()
    data["relevance_category"] = data["relevance_category"].fillna("Other").astype(str).str.strip()
    data.loc[~data["relevance_category"].isin(NEWS_CATEGORIES), "relevance_category"] = "Other"
    data["relevance_score"] = pd.to_numeric(data["relevance_score"], errors="coerce").fillna(0)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["is_verified"] = data["is_verified"].fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes", "y", "verified", "manual"}
    )
    data["notes"] = data["notes"].fillna("").astype(str).str.strip()
    data = data[data["title"].astype(str).str.len() > 0].copy()
    return data


def load_curated_company_news(path: str | Path = CURATED_NEWS_PATH) -> pd.DataFrame:
    news_path = Path(path)
    if not news_path.exists():
        return pd.DataFrame(columns=NEWS_REQUIRED_COLUMNS)
    try:
        raw = pd.read_csv(news_path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=NEWS_REQUIRED_COLUMNS)
    return _ensure_news_columns(raw)


def filter_company_news(
    news_df: pd.DataFrame,
    company: str,
    country: str,
) -> pd.DataFrame:
    if news_df is None or news_df.empty:
        return pd.DataFrame(columns=NEWS_REQUIRED_COLUMNS)
    data = _ensure_news_columns(news_df)
    country_norm = str(country or "").strip().upper()
    if country_norm:
        data = data[(data["country"] == country_norm) | (data["country"] == "")].copy()
    if company == "TODAS":
        return rank_company_news_relevance(data)

    company_norm = normalize_text(company)
    exact = data[data["company_name_norm"] == company_norm].copy()
    if not exact.empty:
        return rank_company_news_relevance(exact)

    contains = data[
        data["company_name"].map(normalize_text).str.contains(company_norm, regex=False, na=False)
        | data["company_name_norm"].str.contains(company_norm, regex=False, na=False)
    ].copy()
    return rank_company_news_relevance(contains)


def rank_company_news_relevance(news_df: pd.DataFrame) -> pd.DataFrame:
    if news_df is None or news_df.empty:
        return pd.DataFrame(columns=NEWS_REQUIRED_COLUMNS)
    data = _ensure_news_columns(news_df)
    data = data.sort_values(
        ["is_verified", "relevance_score", "date"],
        ascending=[False, False, False],
        na_position="last",
    )
    return data.reset_index(drop=True)


def summarize_news_for_brokers(news_df: pd.DataFrame, company: str) -> str:
    if news_df is None or news_df.empty:
        return (
            "No curated news available for the selected company yet. "
            "External news ingestion is planned as a future enhancement."
        )
    categories = news_df["relevance_category"].dropna().astype(str)
    top_category = categories.value_counts().index[0] if not categories.empty else "Other"
    latest_date = news_df["date"].max()
    latest_text = latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else "date not available"
    verified = int(news_df["is_verified"].sum())
    return (
        f"Curated external intelligence for {company} is concentrated in {top_category}. "
        f"The most recent curated item is dated {latest_text}. "
        f"{verified} item(s) are marked as verified/manual. Treat these items as contextual intelligence "
        "and validate source, date and link before formal use."
    )


def generate_news_broker_questions(news_df: pd.DataFrame, company: str) -> list[str]:
    if news_df is None or news_df.empty:
        return [
            f"What public external context should be manually reviewed for {company} before the meeting?",
            "Are there recent regulatory, strategic or capital developments that should be validated from official sources?",
            "Should the broker team add curated news or leadership references before using this externally?",
        ]
    categories = set(news_df["relevance_category"].dropna().astype(str))
    questions = []
    if "Strategy" in categories:
        questions.append("How does the company view the strategic initiative mentioned in recent public news?")
    if "Product / Distribution" in categories:
        questions.append("Could recent distribution or product changes affect growth in key lines?")
    if "Regulation" in categories:
        questions.append("Are recent regulatory developments expected to affect underwriting or reinsurance needs?")
    if "Claims / Catastrophe" in categories:
        questions.append("Could recent claims or catastrophe context affect retention, limits or treaty structure?")
    if "Reinsurance / Capital" in categories:
        questions.append("Does recent capital or reinsurance context suggest a renewal discussion angle?")
    if "Technology / AI" in categories:
        questions.append("Could technology or AI initiatives change distribution, risk selection or operations?")
    if "Leadership" in categories:
        questions.append("Should any manually curated leadership changes be considered in meeting preparation?")
    questions.append("Which source links should be validated before using this intelligence in a client discussion?")
    return list(dict.fromkeys(questions))[:6]


def build_company_news_context(
    news_df: pd.DataFrame,
    selected_company: str,
    selected_country: str,
    selected_line: str,
    selected_years: list[int],
) -> dict:
    filtered = filter_company_news(news_df, selected_company, selected_country)
    latest_date = filtered["date"].max() if not filtered.empty else pd.NaT
    categories = filtered["relevance_category"].dropna().astype(str) if not filtered.empty else pd.Series(dtype=str)
    top_category = categories.value_counts().index[0] if not categories.empty else "N/A"
    verified_count = int(filtered["is_verified"].sum()) if not filtered.empty else 0
    summary = summarize_news_for_brokers(filtered, selected_company)
    questions = generate_news_broker_questions(filtered, selected_company)
    display = filtered.copy()
    if not display.empty:
        display["date_display"] = display["date"].dt.strftime("%Y-%m-%d").fillna("Date not available")
        display["verification_status"] = display["is_verified"].map(lambda value: "Verified/manual" if value else "Manual/unverified")
    return {
        "selected_company": selected_company,
        "selected_country": selected_country,
        "selected_line": selected_line,
        "selected_years": [int(year) for year in selected_years] if selected_years else [],
        "news_items": display,
        "total_items": int(len(filtered)),
        "latest_news_date": latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else "N/A",
        "top_relevance_category": top_category,
        "verified_items": verified_count,
        "recent_topics": categories.value_counts().to_dict() if not categories.empty else {},
        "broker_relevance_summary": summary,
        "suggested_questions": questions,
        "limitations": [
            "Current version uses curated/manual news only.",
            "It is not a live news feed yet.",
            "News should be validated before formal use.",
            "Key people / leadership search is not yet connected unless manually curated.",
        ],
    }


def load_key_people_template(path: str | Path = KEY_PEOPLE_TEMPLATE_PATH) -> pd.DataFrame:
    columns = [
        "company_name",
        "role",
        "person_name",
        "source",
        "source_url",
        "last_verified_date",
        "notes",
    ]
    people_path = Path(path)
    if not people_path.exists():
        return pd.DataFrame(columns=columns)
    try:
        data = pd.read_csv(people_path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in data.columns:
            data[column] = pd.NA
    return data[columns].copy()


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
