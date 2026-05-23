import hashlib
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

from .config import PipelineConfig, ensure_pipeline_dirs
from .discover_fasecolda_sources import load_discovered_or_registry
from .pipeline_logger import append_event, now_iso, write_status


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _period_folder(period: object) -> str:
    text = "" if pd.isna(period) else str(period).strip()
    return text or "undated"


def _target_path(config: PipelineConfig, row: pd.Series) -> Path:
    file_name = str(row.get("file_name") or Path(urlparse(str(row.get("file_url", ""))).path).name)
    return config.raw_dir / str(row.get("source_name", "unknown_source")) / _period_folder(row.get("detected_period")) / file_name


def download_sources(config: PipelineConfig) -> pd.DataFrame:
    ensure_pipeline_dirs(config)
    sources = load_discovered_or_registry(config)
    manifest_rows: list[dict] = []
    downloaded = 0

    for _, row in sources.iterrows():
        file_url = str(row.get("file_url", "")).strip()
        if not file_url:
            manifest_rows.append(
                {
                    "source_name": row.get("source_name", ""),
                    "file_url": file_url,
                    "local_path": "",
                    "file_name": row.get("file_name", ""),
                    "downloaded_at": "",
                    "file_hash": "",
                    "file_size_bytes": 0,
                    "status": "skipped_no_direct_file_url",
                    "error_message": "Discovery returned a landing page or manual registry entry, not a direct file URL.",
                }
            )
            continue

        target = _target_path(config, row)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if target.exists() and target.stat().st_size > 0:
                status = "already_present"
            else:
                response = requests.get(file_url, timeout=60, stream=True)
                response.raise_for_status()
                with target.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                downloaded += 1
                status = "downloaded"

            manifest_rows.append(
                {
                    "source_name": row.get("source_name", ""),
                    "file_url": file_url,
                    "local_path": str(target),
                    "file_name": target.name,
                    "downloaded_at": now_iso(),
                    "file_hash": sha256_file(target),
                    "file_size_bytes": target.stat().st_size,
                    "status": status,
                    "error_message": "",
                }
            )
        except Exception as exc:
            manifest_rows.append(
                {
                    "source_name": row.get("source_name", ""),
                    "file_url": file_url,
                    "local_path": str(target),
                    "file_name": target.name,
                    "downloaded_at": now_iso(),
                    "file_hash": "",
                    "file_size_bytes": 0,
                    "status": "error",
                    "error_message": str(exc),
                }
            )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(config.source_manifest_path, index=False, encoding="utf-8-sig")
    append_event(config, "download", "PASS", f"Download step finished. New files downloaded: {downloaded}.")
    write_status(
        config,
        {
            "mode": "download",
            "discovery_status": "available" if not sources.empty else "not_available",
            "files_downloaded": downloaded,
            "files_processed": 0,
            "validation_status": "not_run",
            "latest_available_period": "N/A",
            "database_status": "unchanged",
            "automation_mode": "Manual run only",
            "message": "Downloader stores only direct downloadable files and skips landing-page registry entries.",
        },
    )
    return manifest

