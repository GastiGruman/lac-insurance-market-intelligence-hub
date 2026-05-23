from datetime import datetime

import duckdb
import pandas as pd

from .config import PipelineConfig, ensure_pipeline_dirs
from .pipeline_logger import append_event
from .process_ciudades_ramos import normalize_text


SOURCE_NAME = "FASECOLDA - INDICADORES DE GESTION"


def process_indicadores_gestion(config: PipelineConfig) -> pd.DataFrame:
    """Create a normalized continuity extract from the current exploratory DuckDB table.

    The existing Indicadores parser is source-file specific. For Phase 3 we keep the
    trusted demo snapshot unchanged and export the loaded table into a normalized
    processed artifact so validation and candidate database steps remain auditable.
    """
    ensure_pipeline_dirs(config)
    if not config.current_db_path.exists():
        append_event(config, "process_indicadores_gestion", "WARNING", "Current DuckDB snapshot not available.")
        return pd.DataFrame()

    try:
        conn = duckdb.connect(str(config.current_db_path), read_only=True)
        try:
            df = conn.execute("SELECT * FROM fact_indicadores_gestion_2025").fetchdf()
        finally:
            conn.close()
    except Exception as exc:
        append_event(config, "process_indicadores_gestion", "WARNING", f"Could not export current Indicadores table: {exc}")
        return pd.DataFrame()

    if df.empty:
        append_event(config, "process_indicadores_gestion", "WARNING", "Indicadores table is empty.")
        return df

    df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
    wide = (
        df.pivot_table(
            index=[
                "country", "source", "year", "month", "period_date", "company_local",
                "company_standard", "line_of_business_local", "line_of_business_standard",
                "source_file",
            ],
            columns="metric_name",
            values="metric_value",
            aggfunc="sum",
        )
        .reset_index()
    )
    wide.columns.name = None
    rename_map = {
        "company_local": "company_name",
        "company_standard": "company_name_standard",
        "line_of_business_local": "line_of_business",
    }
    wide = wide.rename(columns=rename_map)
    wide["company_name_norm"] = wide["company_name"].map(normalize_text)
    wide["line_of_business_norm"] = wide["line_of_business"].map(normalize_text)
    wide["lob_group"] = pd.NA
    wide["city"] = pd.NA
    wide["department"] = pd.NA
    wide["source_sheet"] = wide["line_of_business"]
    wide["update_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for column in [
        "gross_written_premium", "claims", "loss_ratio", "retained_premium",
        "reinsurance_ceded_premium", "reinsurance_cession_ratio", "retention_ratio",
        "paid_claims",
    ]:
        if column not in wide.columns:
            wide[column] = pd.NA

    output_columns = [
        "country", "source", "year", "month", "period_date", "company_name",
        "company_name_norm", "company_name_standard", "line_of_business",
        "line_of_business_norm", "line_of_business_standard", "lob_group", "city",
        "department", "gross_written_premium", "claims", "loss_ratio",
        "retained_premium", "reinsurance_ceded_premium", "reinsurance_cession_ratio",
        "retention_ratio", "paid_claims", "source_file", "source_sheet", "update_date",
    ]
    wide = wide[output_columns]
    wide.to_csv(config.processed_dir / "indicadores_gestion_normalized.csv", index=False, encoding="utf-8-sig")
    append_event(
        config,
        "process_indicadores_gestion",
        "PASS",
        f"Exported {len(wide):,} normalized Indicadores rows from current DuckDB snapshot.",
    )
    return wide

