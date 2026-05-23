import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

from .config import PipelineConfig, ensure_pipeline_dirs
from .pipeline_logger import append_event, now_iso, write_status
from .source_registry import configured_source_pages, manual_source_registry


DOWNLOAD_EXTENSIONS = (".xls", ".xlsx", ".csv", ".zip")


def _looks_relevant(link_text: str, href: str, keywords: list[str]) -> bool:
    combined = f"{link_text} {href}".lower()
    return any(keyword.lower() in combined for keyword in keywords)


def _file_type_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix or "unknown"


def _detect_period(text: str) -> str:
    match = re.search(r"(20\d{2})(?:[-_ ]?(0[1-9]|1[0-2]))?", text)
    if not match:
        return ""
    year, month = match.group(1), match.group(2)
    return f"{year}-{month}" if month else year


def discover_sources(config: PipelineConfig, timeout: int = 20) -> pd.DataFrame:
    ensure_pipeline_dirs(config)
    records: list[dict] = []
    discovery_errors: list[str] = []

    for source in configured_source_pages():
        try:
            response = requests.get(
                source["source_page"],
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 Colombia insurance market intelligence demo"},
            )
            response.raise_for_status()
            html = response.text
            links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S)
            for href, raw_text in links:
                text = re.sub(r"<[^>]+>", " ", raw_text)
                absolute_url = urljoin(source["source_page"], href)
                if not absolute_url.lower().endswith(DOWNLOAD_EXTENSIONS):
                    continue
                if not _looks_relevant(text, absolute_url, source["keywords"]):
                    continue
                file_name = Path(urlparse(absolute_url).path).name
                records.append(
                    {
                        "source_name": source["source_name"],
                        "display_name": source["display_name"],
                        "file_url": absolute_url,
                        "file_name": file_name,
                        "detected_period": _detect_period(file_name or text),
                        "file_type": _file_type_from_url(absolute_url),
                        "discovered_at": now_iso(),
                        "source_page": source["source_page"],
                        "status": "discovered",
                        "expected_pattern": "",
                        "notes": text.strip(),
                    }
                )
        except Exception as exc:
            discovery_errors.append(f"{source['display_name']}: {exc}")

    if not records:
        message = "Source discovery failed; using manual registry fallback"
        append_event(config, "discover", "WARNING", message, errors=" | ".join(discovery_errors))
        records = manual_source_registry()
        discovery_status = "fallback"
    else:
        discovery_status = "discovered"
        append_event(config, "discover", "PASS", f"Discovered {len(records)} downloadable source links.")

    df = pd.DataFrame(records)
    df.to_csv(config.discovered_sources_path, index=False, encoding="utf-8-sig")
    write_status(
        config,
        {
            "mode": "discover",
            "discovery_status": discovery_status,
            "files_downloaded": 0,
            "files_processed": 0,
            "validation_status": "not_run",
            "latest_available_period": df["detected_period"].replace("", pd.NA).dropna().max() if not df.empty else "N/A",
            "database_status": "unchanged",
            "automation_mode": "Manual run only",
            "message": "Discovery metadata written. Download requires direct downloadable file URLs.",
        },
    )
    return df


def load_discovered_or_registry(config: PipelineConfig) -> pd.DataFrame:
    if config.discovered_sources_path.exists():
        return pd.read_csv(config.discovered_sources_path)
    return pd.DataFrame(manual_source_registry())

