import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PipelineConfig, ensure_pipeline_dirs


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append_event(config: PipelineConfig, event_type: str, status: str, message: str, **extra: Any) -> None:
    ensure_pipeline_dirs(config)
    path = config.metadata_dir / "pipeline_events.csv"
    row = {
        "event_time": now_iso(),
        "event_type": event_type,
        "status": status,
        "message": message,
        **extra,
    }
    new_df = pd.DataFrame([row])
    if path.exists():
        old_df = pd.read_csv(path)
        new_df = pd.concat([old_df, new_df], ignore_index=True)
    new_df.to_csv(path, index=False, encoding="utf-8-sig")


def write_status(config: PipelineConfig, status: dict[str, Any]) -> None:
    ensure_pipeline_dirs(config)
    status = {"updated_at": now_iso(), **status}
    config.latest_status_json_path.write_text(
        json.dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Latest Pipeline Status",
        "",
        f"- Updated at: {status.get('updated_at', 'N/A')}",
        f"- Last run mode: {status.get('mode', 'N/A')}",
        f"- Source discovery status: {status.get('discovery_status', 'N/A')}",
        f"- Files downloaded: {status.get('files_downloaded', 'N/A')}",
        f"- Files processed: {status.get('files_processed', 'N/A')}",
        f"- Validation status: {status.get('validation_status', 'N/A')}",
        f"- Latest available period: {status.get('latest_available_period', 'N/A')}",
        f"- Database status: {status.get('database_status', 'N/A')}",
        f"- Automation mode: {status.get('automation_mode', 'Manual run only')}",
        "",
        status.get("message", ""),
    ]
    config.latest_status_md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def read_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

