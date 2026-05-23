import json
from pathlib import Path

import duckdb
import pandas as pd

from .config import PipelineConfig, ensure_pipeline_dirs
from .pipeline_logger import append_event, write_status


REQUIRED_NORMALIZED_COLUMNS = [
    "country", "source", "year", "month", "period_date", "company_name",
    "company_name_standard", "line_of_business", "line_of_business_standard",
    "gross_written_premium", "claims", "source_file", "update_date",
]


def _read_csv_if_available(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _add_result(results: list[dict], test_name: str, result: str, detail: str, record_count: int = 0) -> None:
    results.append(
        {
            "test_name": test_name,
            "result": result,
            "detail": detail,
            "record_count": record_count,
        }
    )


def _validate_dataframe(df: pd.DataFrame, source_label: str, results: list[dict]) -> None:
    if df.empty:
        _add_result(results, f"{source_label} availability", "WARNING", "No processed rows available.")
        return

    missing = [column for column in REQUIRED_NORMALIZED_COLUMNS if column not in df.columns]
    if missing:
        _add_result(results, f"{source_label} required columns", "ERROR", f"Missing columns: {missing}")
        return
    _add_result(results, f"{source_label} required columns", "PASS", "All required columns are present.", len(df))

    working = df.copy()
    working["year"] = pd.to_numeric(working["year"], errors="coerce")
    working["month"] = pd.to_numeric(working["month"], errors="coerce")
    working["period_date"] = pd.to_datetime(working["period_date"], errors="coerce")

    bad_dates = working["period_date"].isna().sum()
    _add_result(
        results,
        f"{source_label} valid period_date",
        "PASS" if bad_dates == 0 else "ERROR",
        f"Rows with invalid period_date: {bad_dates}",
        int(bad_dates),
    )

    bad_months = working["month"].isna().sum() + (~working["month"].between(1, 12)).sum()
    _add_result(
        results,
        f"{source_label} valid month",
        "PASS" if bad_months == 0 else "ERROR",
        f"Rows with invalid month: {int(bad_months)}",
        int(bad_months),
    )

    null_keys = working[
        ["country", "source", "year", "company_name_standard", "line_of_business_standard", "source_file"]
    ].isna().any(axis=1).sum()
    _add_result(
        results,
        f"{source_label} null key fields",
        "PASS" if null_keys == 0 else "ERROR",
        f"Rows with null key fields: {int(null_keys)}",
        int(null_keys),
    )

    for metric in ["gross_written_premium", "claims", "retained_premium", "reinsurance_ceded_premium", "paid_claims"]:
        if metric in working.columns:
            values = pd.to_numeric(working[metric], errors="coerce")
            negative = (values < 0).sum()
            _add_result(
                results,
                f"{source_label} negative {metric}",
                "PASS" if negative == 0 else "WARNING",
                f"Rows with negative {metric}: {int(negative)}",
                int(negative),
            )

    for ratio in ["loss_ratio", "reinsurance_cession_ratio", "retention_ratio"]:
        if ratio in working.columns:
            values = pd.to_numeric(working[ratio], errors="coerce")
            populated = values.dropna()
            if populated.empty:
                _add_result(results, f"{source_label} {ratio} bounds", "WARNING", f"No populated {ratio} values.")
                continue
            out_of_bounds = (~populated.between(-0.2, 1.2)).sum()
            _add_result(
                results,
                f"{source_label} {ratio} bounds",
                "PASS" if out_of_bounds == 0 else "WARNING",
                f"Populated rows outside reasonable bounds: {int(out_of_bounds)}",
                int(out_of_bounds),
            )

    duplicate_keys = working.duplicated(
        subset=[
            "country", "source", "year", "month", "company_name_standard",
            "line_of_business_standard", "city", "source_file",
        ],
        keep=False,
    ).sum()
    _add_result(
        results,
        f"{source_label} duplicate keys",
        "PASS" if duplicate_keys == 0 else "WARNING",
        f"Rows with duplicated audit key: {int(duplicate_keys)}",
        int(duplicate_keys),
    )


def _validate_current_duckdb(config: PipelineConfig, results: list[dict]) -> str:
    if not config.current_db_path.exists():
        _add_result(results, "Current DuckDB availability", "ERROR", "Current DuckDB snapshot is missing.")
        return "N/A"

    try:
        conn = duckdb.connect(str(config.current_db_path), read_only=True)
        try:
            tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
            expected = {
                "fact_market_core", "fact_fasecolda_market", "fact_indicadores_gestion_2025",
                "dim_company_mapping", "dim_line_of_business_mapping",
            }
            missing_tables = sorted(expected - tables)
            _add_result(
                results,
                "Current DuckDB expected tables",
                "PASS" if not missing_tables else "ERROR",
                f"Missing tables: {missing_tables}" if missing_tables else "All expected app tables are present.",
            )
            latest = conn.execute("SELECT MAX(period_date) FROM fact_market_core").fetchone()[0]
            rows = conn.execute("SELECT COUNT(*) FROM fact_market_core").fetchone()[0]
            _add_result(results, "Current DuckDB fact_market_core rows", "PASS", f"Rows available: {rows:,}", int(rows))
            return str(latest)[:10] if latest else "N/A"
        finally:
            conn.close()
    except Exception as exc:
        _add_result(results, "Current DuckDB validation", "ERROR", str(exc))
        return "N/A"


def validate_pipeline_outputs(config: PipelineConfig, mode: str = "validate") -> tuple[pd.DataFrame, bool]:
    ensure_pipeline_dirs(config)
    results: list[dict] = []

    ciudades = _read_csv_if_available(config.processed_dir / "ciudades_ramos_normalized.csv")
    indicadores = _read_csv_if_available(config.processed_dir / "indicadores_gestion_normalized.csv")

    if ciudades.empty and indicadores.empty:
        _add_result(
            results,
            "Processed pipeline outputs",
            "WARNING",
            "No processed pipeline outputs found; validating the current demo DuckDB snapshot only.",
        )
    else:
        _validate_dataframe(ciudades, "Ciudades y Ramos processed output", results)
        _validate_dataframe(indicadores, "Indicadores de Gestion processed output", results)

    latest_period = _validate_current_duckdb(config, results)
    report = pd.DataFrame(results)
    report.to_csv(config.validation_report_path, index=False, encoding="utf-8-sig")
    (config.metadata_dir / "pipeline_validation_report.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    has_errors = (report["result"] == "ERROR").any() if not report.empty else True
    validation_status = "ERROR" if has_errors else ("WARNING" if (report["result"] == "WARNING").any() else "PASS")
    append_event(config, "validate", validation_status, f"Validation finished with status {validation_status}.")
    write_status(
        config,
        {
            "mode": mode,
            "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
            "files_downloaded": 0,
            "files_processed": int(len(ciudades) + len(indicadores)),
            "validation_status": validation_status,
            "latest_available_period": latest_period,
            "database_status": "unchanged",
            "automation_mode": "Manual run only",
            "message": "Validation warnings are review signals. Errors prevent database promotion.",
        },
    )
    return report, has_errors

