from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from app.config.formato_290_metric_mapping import (
    FORMATO_290_DATASET_ID,
    FORMATO_290_METADATA_URL,
    FORMATO_290_SOURCE_URL,
)


class Formato290ApiError(RuntimeError):
    """Raised when the Formato 290 API cannot be reached or verified."""


def fetch_metadata(timeout: int = 60) -> dict[str, Any]:
    response = requests.get(FORMATO_290_METADATA_URL, timeout=timeout)
    response.raise_for_status()
    metadata = response.json()
    name = str(metadata.get("name", ""))
    attribution = str(metadata.get("attribution", ""))
    if "Formato 290" not in name:
        raise Formato290ApiError(f"Dataset name does not confirm Formato 290: {name}")
    if "Superintendencia Financiera" not in attribution:
        raise Formato290ApiError(f"Dataset attribution does not confirm SFC: {attribution}")
    return metadata


def metadata_columns(metadata: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for col in metadata.get("columns", []):
        if col.get("fieldName"):
            rows.append(
                {
                    "dataset_id": FORMATO_290_DATASET_ID,
                    "column_name": col.get("name"),
                    "api_field_name": col.get("fieldName"),
                    "data_type": col.get("dataTypeName"),
                    "description": col.get("description"),
                    "position": col.get("position"),
                }
            )
    return pd.DataFrame(rows)


def fetch_count(timeout: int = 60) -> int:
    response = requests.get(
        FORMATO_290_SOURCE_URL,
        params={"$select": "count(*)"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        return 0
    return int(payload[0].get("count", 0))


def fetch_page(limit: int, offset: int, timeout: int = 120) -> pd.DataFrame:
    response = requests.get(
        FORMATO_290_SOURCE_URL,
        params={"$limit": limit, "$offset": offset},
        timeout=timeout,
    )
    response.raise_for_status()
    return pd.DataFrame(response.json())


def download_all_rows(limit: int = 50000, timeout: int = 120) -> pd.DataFrame:
    total = fetch_count(timeout=timeout)
    pages = []
    for offset in range(0, total, limit):
        page = fetch_page(limit=limit, offset=offset, timeout=timeout)
        if page.empty:
            break
        pages.append(page)
    if not pages:
        return pd.DataFrame()
    return pd.concat(pages, ignore_index=True)

