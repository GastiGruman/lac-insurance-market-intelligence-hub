from __future__ import annotations

import logging
import re
import shutil
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from app.config.formato_290_metric_mapping import (
    FORMATO_290_DATASET_ID,
    FORMATO_290_SOURCE_NAME,
    FORMATO_290_SOURCE_URL,
    ID_COLUMNS,
    LOSS_RATIO_DEFINITION,
    METRIC_MAPPING_RULES,
)
from app.data_sources.formato_290_api import download_all_rows, fetch_metadata, metadata_columns
from app.validation.formato_290_validation import validate_formato_290_frames

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data/database/insurance_market.duckdb"
RAW_DIR = PROJECT_ROOT / "data/raw/formato_290"
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DICTIONARY_DIR = PROJECT_ROOT / "outputs/data_dictionary"
OUTPUT_QUALITY_DIR = PROJECT_ROOT / "outputs/data_quality"
OUTPUT_VALIDATION_DIR = PROJECT_ROOT / "outputs/validation"
OUTPUT_RECONCILIATION_DIR = PROJECT_ROOT / "outputs/reconciliation"
REFERENCE_DIR = PROJECT_ROOT / "data/reference"

RAW_TABLE = "raw_formato_290"
CLEAN_TABLE = "clean_formato_290"
MAPPING_TABLE = "formato_290_metric_mapping_status"
VALIDATION_TABLE = "validation_formato_290"
FACT_CORE_TABLE = "fact_market_core_formato_290"

RAW_METADATA_COLUMNS = {
    "ingestion_timestamp",
    "source_dataset_id",
    "source_url",
    "raw_file_name",
    "extraction_method",
}


def ensure_dirs() -> None:
    for folder in [
        RAW_DIR,
        LOG_DIR,
        OUTPUT_DICTIONARY_DIR,
        OUTPUT_QUALITY_DIR,
        OUTPUT_VALIDATION_DIR,
        OUTPUT_RECONCILIATION_DIR,
        REFERENCE_DIR,
        DB_PATH.parent,
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def configure_logging() -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger("formato_290_update")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "formato_290_update.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().lower()
    return text


def normalize_company(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = re.sub(r"^\d+\-\d+\s*", "", text)
    text = text.replace('"', "").replace("'", "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_ramo(value: object) -> str:
    text = str(value).strip().replace("_", " ") if pd.notna(value) else ""
    text = re.sub(r"\s+MES$", "", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def company_clean_sql() -> str:
    return """
        upper(
            trim(
                regexp_replace(
                    replace(
                        replace(
                            regexp_replace(coalesce(nombre_entidad, ''), '^[0-9]+-[0-9]+\\s*', ''),
                            '''',
                            ''
                        ),
                        '"',
                        ''
                    ),
                    '\\s+',
                    ' ',
                    'g'
                )
            )
        )
    """


def ramo_clean_sql() -> str:
    return """
        upper(
            trim(
                    regexp_replace(
                    regexp_replace(upper(replace(coalesce(ramo, ''), '_', ' ')), '[ ]+MES$', ''),
                    '\\s+',
                    ' ',
                    'g'
                )
            )
        )
    """


def backup_database(logger: logging.Logger) -> None:
    if not DB_PATH.exists():
        return
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"insurance_market_before_formato_290_{stamp}.duckdb"
    shutil.copy2(DB_PATH, backup_path)
    logger.info("DuckDB backup created at %s", backup_path)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def latest_raw_file() -> Path:
    files = sorted(RAW_DIR.glob("formato_290_raw_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No Formato 290 raw CSV files found in {RAW_DIR}")
    return files[0]


def detect_ramo_columns(raw_df: pd.DataFrame) -> list[str]:
    id_cols = {c for c in raw_df.columns if c.lower() in ID_COLUMNS or c.lower().startswith(":")}
    numeric_candidates: list[str] = []
    for col in raw_df.columns:
        if col in id_cols:
            continue
        numeric = pd.to_numeric(raw_df[col], errors="coerce")
        if numeric.notna().sum() > 0:
            numeric_candidates.append(col)
    return numeric_candidates


def classify_metric(concept_norm: str) -> tuple[str, str]:
    for metric_name, candidates in METRIC_MAPPING_RULES.items():
        for terms in candidates:
            if all(term in concept_norm for term in terms):
                return metric_name, "MAPPED"
    return "pending_mapping", "PENDING_MAPPING"


def build_clean_table(raw_df: pd.DataFrame, raw_file_name: str, ingestion_timestamp: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw_df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    ramo_cols = detect_ramo_columns(df)
    id_cols = [c for c in df.columns if c not in ramo_cols]

    long_df = df.melt(
        id_vars=id_cols,
        value_vars=ramo_cols,
        var_name="ramo",
        value_name="raw_value",
    )
    long_df["normalized_value"] = pd.to_numeric(long_df["raw_value"], errors="coerce")
    long_df = long_df.dropna(subset=["normalized_value"]).copy()

    year_col = "a_o" if "a_o" in long_df.columns else "ano" if "ano" in long_df.columns else None
    if year_col is None:
        raise ValueError("Formato 290 year column was not found in the API response.")

    long_df["year"] = pd.to_numeric(long_df[year_col], errors="coerce").astype("Int64")
    empty_series = pd.Series(index=long_df.index, dtype="object")
    long_df["month"] = pd.to_numeric(long_df["mes"] if "mes" in long_df.columns else empty_series, errors="coerce").astype("Int64")
    long_df["period_date"] = pd.to_datetime(
        long_df["year"].astype("string") + "-" + long_df["month"].astype("string") + "-01",
        errors="coerce",
    )
    long_df["company_code"] = (long_df["codigo_entidad"] if "codigo_entidad" in long_df.columns else empty_series).astype("string")
    long_df["company_name"] = (long_df["nombre_entidad"] if "nombre_entidad" in long_df.columns else empty_series).astype("string")
    long_df["company_standard"] = long_df["company_name"].map(normalize_company)
    long_df["ramo"] = long_df["ramo"].map(normalize_ramo)
    long_df["ramo_standard"] = long_df["ramo"]
    long_df["unidad_de_captura"] = pd.to_numeric(
        long_df["unidad_de_captura"] if "unidad_de_captura" in long_df.columns else empty_series,
        errors="coerce",
    ).astype("Int64")
    long_df["nombre_unidad_de_captura"] = (
        long_df["nombre_unidad_de_captura"] if "nombre_unidad_de_captura" in long_df.columns else empty_series
    ).astype("string")
    long_df["subcuenta"] = pd.to_numeric(
        long_df["subcuenta"] if "subcuenta" in long_df.columns else empty_series,
        errors="coerce",
    ).astype("Int64")
    long_df["nombre_subcuenta"] = (
        long_df["nombre_subcuenta"] if "nombre_subcuenta" in long_df.columns else empty_series
    ).astype("string")
    long_df["concept_name"] = (
        long_df["nombre_unidad_de_captura"].fillna("")
        + " | "
        + long_df["nombre_subcuenta"].fillna("")
    ).str.strip(" |")
    long_df["concept_norm"] = long_df["concept_name"].map(normalize_text)
    classified = long_df["concept_norm"].map(classify_metric)
    long_df["metric_name"] = classified.map(lambda item: item[0])
    long_df["mapping_status"] = classified.map(lambda item: item[1])
    long_df["currency"] = "COP"
    long_df["unit"] = "pesos"
    long_df.loc[long_df["unidad_de_captura"].eq(19), "unit"] = "millones de pesos"
    long_df.loc[long_df["unidad_de_captura"].eq(20), "unit"] = "unidades"
    long_df["source"] = FORMATO_290_SOURCE_NAME
    long_df["source_dataset_id"] = FORMATO_290_DATASET_ID
    long_df["source_url"] = FORMATO_290_SOURCE_URL
    long_df["raw_file_name"] = raw_file_name
    long_df["extraction_method"] = "Socrata API pagination"
    long_df["ingestion_timestamp"] = ingestion_timestamp

    clean_cols = [
        "period_date",
        "year",
        "month",
        "company_code",
        "company_name",
        "company_standard",
        "ramo",
        "ramo_standard",
        "unidad_de_captura",
        "nombre_unidad_de_captura",
        "subcuenta",
        "nombre_subcuenta",
        "concept_name",
        "metric_name",
        "mapping_status",
        "raw_value",
        "normalized_value",
        "currency",
        "unit",
        "source",
        "source_dataset_id",
        "source_url",
        "raw_file_name",
        "extraction_method",
        "ingestion_timestamp",
    ]
    clean_df = long_df[clean_cols].copy()

    mapping_status = (
        clean_df.groupby(["metric_name", "mapping_status", "concept_name"], dropna=False)
        .agg(records=("normalized_value", "count"), total_value=("normalized_value", "sum"))
        .reset_index()
        .sort_values(["mapping_status", "metric_name", "concept_name"])
    )
    return clean_df, mapping_status


def build_dashboard_metrics(clean_df: pd.DataFrame) -> pd.DataFrame:
    mapped = clean_df[clean_df["mapping_status"].eq("MAPPED")].copy()
    if mapped.empty:
        return pd.DataFrame()
    group_cols = [
        "period_date",
        "year",
        "month",
        "company_code",
        "company_name",
        "company_standard",
        "ramo",
        "ramo_standard",
        "metric_name",
    ]
    return (
        mapped.groupby(group_cols, dropna=False, as_index=False)
        .agg(metric_value=("normalized_value", "sum"))
        .assign(
            country="COLOMBIA",
            region="LATIN AMERICA AND CARIBBEAN",
            regulator="SUPERINTENDENCIA FINANCIERA DE COLOMBIA",
            source=FORMATO_290_SOURCE_NAME,
            currency="COP",
            source_file=lambda x: FORMATO_290_DATASET_ID,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    )


def build_fact_market_core_formato_290(dashboard_df: pd.DataFrame) -> pd.DataFrame:
    if dashboard_df.empty:
        return pd.DataFrame()
    mapping = {"gross_written_premium": "gross_written_premium"}
    available_metrics = set(dashboard_df["metric_name"].dropna())
    if LOSS_RATIO_DEFINITION["preferred_numerator"] in available_metrics:
        mapping[LOSS_RATIO_DEFINITION["preferred_numerator"]] = "claims"
    elif LOSS_RATIO_DEFINITION["fallback_numerator"] in available_metrics:
        mapping[LOSS_RATIO_DEFINITION["fallback_numerator"]] = "claims"

    core = dashboard_df[dashboard_df["metric_name"].isin(mapping)].copy()
    if core.empty:
        return pd.DataFrame()
    core["metric_name"] = core["metric_name"].map(mapping)
    core["company_local"] = core["company_name"]
    core["line_of_business_local"] = core["ramo"]
    core["line_of_business_standard"] = core["ramo_standard"]
    core["city"] = "NACIONAL"
    return core[
        [
            "country",
            "region",
            "regulator",
            "source",
            "period_date",
            "year",
            "month",
            "company_local",
            "company_standard",
            "line_of_business_local",
            "line_of_business_standard",
            "city",
            "metric_name",
            "metric_value",
            "currency",
            "source_file",
            "updated_at",
        ]
    ]


def write_outputs(
    metadata_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    mapping_status: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> None:
    metadata_df.to_csv(OUTPUT_DICTIONARY_DIR / "formato_290_columns.csv", index=False, encoding="utf-8-sig")
    concepts = (
        clean_df.groupby(["unidad_de_captura", "nombre_unidad_de_captura", "subcuenta", "nombre_subcuenta", "concept_name", "metric_name", "mapping_status"], dropna=False)
        .agg(records=("normalized_value", "count"), total_value=("normalized_value", "sum"))
        .reset_index()
        .sort_values(["unidad_de_captura", "subcuenta"])
    )
    concepts.to_csv(OUTPUT_DICTIONARY_DIR / "formato_290_concepts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"company_name": sorted(clean_df["company_standard"].dropna().unique())}).to_csv(
        OUTPUT_QUALITY_DIR / "formato_290_company_completeness.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame({"ramo": sorted(clean_df["ramo_standard"].dropna().unique())}).to_csv(
        OUTPUT_QUALITY_DIR / "formato_290_ramo_completeness.csv", index=False, encoding="utf-8-sig"
    )
    clean_df.groupby(["year", "month"], dropna=False).size().reset_index(name="records").to_csv(
        OUTPUT_QUALITY_DIR / "formato_290_period_coverage.csv", index=False, encoding="utf-8-sig"
    )
    null_checks = pd.DataFrame(
        [{"column": col, "null_rows": int(clean_df[col].isna().sum()), "total_rows": len(clean_df)} for col in clean_df.columns]
    )
    null_checks.to_csv(OUTPUT_QUALITY_DIR / "formato_290_null_checks.csv", index=False, encoding="utf-8-sig")
    mapping_status.to_csv(OUTPUT_QUALITY_DIR / "formato_290_metric_mapping_status.csv", index=False, encoding="utf-8-sig")
    validation_df.to_csv(OUTPUT_VALIDATION_DIR / "formato_290_validation_results.csv", index=False, encoding="utf-8-sig")

    template = pd.DataFrame(
        columns=[
            "metric_name",
            "period",
            "company",
            "ramo",
            "official_value",
            "dashboard_value",
            "difference",
            "percentage_difference",
            "tolerance_absolute",
            "tolerance_percentage",
            "status",
            "comments",
        ]
    )
    template.to_csv(REFERENCE_DIR / "formato_290_reconciliation_template.csv", index=False, encoding="utf-8-sig")


def write_duckdb(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    mapping_status: pd.DataFrame,
    dashboard_df: pd.DataFrame,
    fact_core_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    backup_database(logger)
    conn = duckdb.connect(str(DB_PATH))
    try:
        for table_name, frame in [
            (RAW_TABLE, raw_df),
            (CLEAN_TABLE, clean_df),
            (MAPPING_TABLE, mapping_status),
            ("mart_formato_290_dashboard_metrics", dashboard_df),
            (FACT_CORE_TABLE, fact_core_df),
            (VALIDATION_TABLE, validation_df),
        ]:
            conn.register("frame_to_write", frame)
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM frame_to_write")
            conn.unregister("frame_to_write")
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_premiums AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('gross_written_premium','direct_written_premium','accepted_premium','ceded_premium','retained_premium','earned_premium')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_claims AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('claims_paid','claims_incurred','claims_liquidated')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_commissions AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('commissions','intermediary_charges','discounts')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_reinsurance AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('ceded_premium','accepted_premium','retained_premium')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_technical_result AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('technical_result','technical_reserves','administrative_expenses')
            """
        )
    finally:
        conn.close()


def _mapping_case_sql() -> str:
    return """
        CASE
            WHEN unidad_de_captura = 1 AND subcuenta = 5 THEN 'direct_written_premium'
            WHEN unidad_de_captura = 1 AND subcuenta = 10 THEN 'accepted_premium'
            WHEN unidad_de_captura = 1 AND subcuenta IN (20, 25) THEN 'accepted_reinsurance_premium'
            WHEN unidad_de_captura = 1 AND subcuenta IN (15, 30, 45) THEN 'premium_cancellations'
            WHEN unidad_de_captura = 1 AND subcuenta IN (35, 40) THEN 'ceded_premium'
            WHEN unidad_de_captura = 1 AND subcuenta IN (55, 60, 65) THEN 'discounts'
            WHEN unidad_de_captura = 1 AND subcuenta = 999 THEN 'retained_premium'
            WHEN unidad_de_captura = 2 THEN 'technical_reserves'
            WHEN unidad_de_captura = 3 AND subcuenta = 999 THEN 'earned_premium'
            WHEN unidad_de_captura = 5 AND subcuenta = 999 THEN 'claims_liquidated'
            WHEN unidad_de_captura = 6 AND subcuenta = 999 THEN 'claims_reimbursements'
            WHEN unidad_de_captura = 7 AND subcuenta = 999 THEN 'recoveries_salvage'
            WHEN unidad_de_captura = 8 AND subcuenta = 999 THEN 'claims_incurred'
            WHEN unidad_de_captura = 9 AND subcuenta = 5 THEN 'reinsurance_commissions'
            WHEN unidad_de_captura = 11 AND subcuenta = 999 THEN 'administrative_expenses'
            WHEN unidad_de_captura = 12 AND subcuenta = 999 THEN 'commissions'
            WHEN unidad_de_captura = 14 AND subcuenta = 999 THEN 'technical_result'
            WHEN unidad_de_captura = 21 AND subcuenta = 999 THEN 'reinsurance_ceded_premium'
            WHEN unidad_de_captura = 26 AND subcuenta = 999 THEN 'intermediary_charges_asset_balance'
            WHEN unidad_de_captura = 27 AND subcuenta = 999 THEN 'intermediary_charges'
            ELSE 'pending_mapping'
        END
    """


def _create_outputs_from_duckdb(conn: duckdb.DuckDBPyConnection) -> None:
    metadata_df = conn.execute(f"DESCRIBE {RAW_TABLE}").fetchdf()
    metadata_df = metadata_df.rename(columns={"column_name": "api_field_name", "column_type": "data_type"})
    metadata_df["dataset_id"] = FORMATO_290_DATASET_ID
    metadata_df["column_name"] = metadata_df["api_field_name"]
    metadata_df[["dataset_id", "column_name", "api_field_name", "data_type", "null"]].to_csv(
        OUTPUT_DICTIONARY_DIR / "formato_290_columns.csv", index=False, encoding="utf-8-sig"
    )
    conn.execute(
        f"""
        COPY (
            SELECT
                unidad_de_captura,
                nombre_unidad_de_captura,
                subcuenta,
                nombre_subcuenta,
                concept_name,
                metric_name,
                mapping_status,
                COUNT(*) AS records,
                SUM(normalized_value) AS total_value
            FROM {CLEAN_TABLE}
            GROUP BY ALL
            ORDER BY unidad_de_captura, subcuenta, metric_name
        ) TO '{(OUTPUT_DICTIONARY_DIR / "formato_290_concepts.csv").as_posix()}'
        (HEADER, DELIMITER ',')
        """
    )
    conn.execute(
        f"""
        COPY (
            SELECT company_standard AS company_name, COUNT(*) AS records
            FROM {CLEAN_TABLE}
            GROUP BY company_standard
            ORDER BY company_standard
        ) TO '{(OUTPUT_QUALITY_DIR / "formato_290_company_completeness.csv").as_posix()}'
        (HEADER, DELIMITER ',')
        """
    )
    conn.execute(
        f"""
        COPY (
            SELECT ramo_standard AS ramo, COUNT(*) AS records
            FROM {CLEAN_TABLE}
            GROUP BY ramo_standard
            ORDER BY ramo_standard
        ) TO '{(OUTPUT_QUALITY_DIR / "formato_290_ramo_completeness.csv").as_posix()}'
        (HEADER, DELIMITER ',')
        """
    )
    conn.execute(
        f"""
        COPY (
            SELECT year, month, COUNT(*) AS records
            FROM {CLEAN_TABLE}
            GROUP BY year, month
            ORDER BY year, month
        ) TO '{(OUTPUT_QUALITY_DIR / "formato_290_period_coverage.csv").as_posix()}'
        (HEADER, DELIMITER ',')
        """
    )
    null_rows = []
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {CLEAN_TABLE}").fetchone()[0]
    for col in conn.execute(f"DESCRIBE {CLEAN_TABLE}").fetchdf()["column_name"].tolist():
        null_count = conn.execute(f"SELECT COUNT(*) FROM {CLEAN_TABLE} WHERE {quote_ident(col)} IS NULL").fetchone()[0]
        null_rows.append({"column": col, "null_rows": null_count, "total_rows": total_rows})
    pd.DataFrame(null_rows).to_csv(OUTPUT_QUALITY_DIR / "formato_290_null_checks.csv", index=False, encoding="utf-8-sig")
    conn.execute(
        f"""
        COPY (
            SELECT metric_name, mapping_status, concept_name, COUNT(*) AS records, SUM(normalized_value) AS total_value
            FROM {CLEAN_TABLE}
            GROUP BY metric_name, mapping_status, concept_name
            ORDER BY mapping_status, metric_name, concept_name
        ) TO '{(OUTPUT_QUALITY_DIR / "formato_290_metric_mapping_status.csv").as_posix()}'
        (HEADER, DELIMITER ',')
        """
    )


def _create_validation_from_duckdb(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    rows = []
    now = datetime.now().isoformat(timespec="seconds")

    def add(check_name: str, status: str, details: str, affected_rows: int | None = None) -> None:
        rows.append(
            {
                "check_name": check_name,
                "status": status,
                "details": details,
                "affected_rows": affected_rows,
                "timestamp": now,
            }
        )

    raw_rows = conn.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
    clean_rows = conn.execute(f"SELECT COUNT(*) FROM {CLEAN_TABLE}").fetchone()[0]
    dashboard_rows = conn.execute("SELECT COUNT(*) FROM mart_formato_290_dashboard_metrics").fetchone()[0]
    add("dataset_downloaded", "PASS" if raw_rows > 0 else "FAIL", f"Raw rows: {raw_rows:,}", raw_rows)
    add("clean_rows_available", "PASS" if clean_rows > 0 else "FAIL", f"Clean non-zero rows: {clean_rows:,}", clean_rows)
    add("dashboard_metrics_available", "PASS" if dashboard_rows > 0 else "WARNING", f"Dashboard metric rows: {dashboard_rows:,}", dashboard_rows)
    latest = conn.execute(f"SELECT MAX(period_date) FROM {CLEAN_TABLE}").fetchone()[0]
    add("latest_period_detected", "PASS" if latest else "FAIL", f"Latest period: {latest}")
    for col in ["year", "month", "company_standard", "ramo_standard", "concept_name", "normalized_value"]:
        nulls = conn.execute(f"SELECT COUNT(*) FROM {CLEAN_TABLE} WHERE {quote_ident(col)} IS NULL").fetchone()[0]
        add(f"null_check_{col}", "PASS" if nulls == 0 else "WARNING", f"Null rows in {col}: {nulls:,}", nulls)
    mapped_metrics = set(
        conn.execute(f"SELECT DISTINCT metric_name FROM {CLEAN_TABLE} WHERE mapping_status = 'MAPPED'").fetchdf()["metric_name"].tolist()
    )
    for metric in [
        "direct_written_premium",
        "earned_premium",
        "claims_incurred",
        "claims_liquidated",
        "commissions",
        "intermediary_charges",
        "technical_result",
    ]:
        add(f"metric_mapping_{metric}", "PASS" if metric in mapped_metrics else "WARNING", f"{metric}: {'mapped' if metric in mapped_metrics else 'pending/unavailable'}")
    denom = conn.execute(
        """
        SELECT SUM(metric_value)
        FROM mart_formato_290_dashboard_metrics
        WHERE metric_name = 'earned_premium'
        """
    ).fetchone()[0]
    numer = conn.execute(
        """
        SELECT SUM(metric_value)
        FROM mart_formato_290_dashboard_metrics
        WHERE metric_name = 'claims_incurred'
        """
    ).fetchone()[0]
    if denom and denom > 0:
        add("loss_ratio_from_totals", "PASS", f"claims_incurred / earned_premium = {float(numer or 0) / float(denom):.4f}")
    else:
        add("loss_ratio_denominator_valid", "WARNING", "Earned premium denominator is zero, negative or unavailable.")
    add("period_basis_review", "WARNING", "Confirm whether Formato 290 values are monthly flow or accumulated before annualizing.")
    return pd.DataFrame(rows)


def process_raw_file(raw_file: Path, logger: logging.Logger, extraction_method: str = "Local raw CSV resume") -> dict[str, object]:
    ensure_dirs()
    raw_file = raw_file.resolve()
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw Formato 290 CSV not found: {raw_file}")
    ingestion_timestamp = datetime.now().isoformat(timespec="seconds")
    started = ingestion_timestamp
    logger.info("Processing Formato 290 raw file: %s", raw_file)
    backup_database(logger)

    conn = duckdb.connect(str(DB_PATH))
    try:
        logger.info("Loading raw CSV into DuckDB")
        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {RAW_TABLE} AS
            SELECT
                *,
                ? AS ingestion_timestamp,
                ? AS source_dataset_id,
                ? AS source_url,
                ? AS raw_file_name,
                ? AS extraction_method
            FROM read_csv_auto(?, all_varchar=true)
            """,
            [ingestion_timestamp, FORMATO_290_DATASET_ID, FORMATO_290_SOURCE_URL, raw_file.name, extraction_method, str(raw_file)],
        )
        raw_columns = conn.execute(f"DESCRIBE {RAW_TABLE}").fetchdf()["column_name"].tolist()
        id_cols = {c for c in raw_columns if c.lower() in ID_COLUMNS or c in RAW_METADATA_COLUMNS}
        ramo_cols = [c for c in raw_columns if c not in id_cols]
        if not ramo_cols:
            raise ValueError("No ramo columns detected in Formato 290 raw file.")
        unpivot_cols = ", ".join(quote_ident(c) for c in ramo_cols)
        mapping_case = _mapping_case_sql()
        company_clean_expr = company_clean_sql()
        ramo_clean_expr = ramo_clean_sql()
        logger.info("Creating clean long-form table from %s ramo columns", len(ramo_cols))
        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {CLEAN_TABLE} AS
            WITH unpivoted AS (
                SELECT *
                FROM {RAW_TABLE}
                UNPIVOT(raw_value FOR ramo IN ({unpivot_cols}))
            ),
            typed AS (
                SELECT
                    make_date(try_cast(a_o AS INTEGER), try_cast(mes AS INTEGER), 1) AS period_date,
                    try_cast(a_o AS INTEGER) AS year,
                    try_cast(mes AS INTEGER) AS month,
                    codigo_entidad AS company_code,
                    nombre_entidad AS company_name_raw,
                    {company_clean_expr} AS company_name_clean,
                    concat(codigo_entidad, ' | ', {company_clean_expr}) AS company_display_name,
                    ramo AS ramo_code,
                    ramo AS ramo_name_raw,
                    {ramo_clean_expr} AS ramo_name_clean,
                    {ramo_clean_expr} AS ramo_display_name,
                    try_cast(unidad_de_captura AS INTEGER) AS unidad_de_captura,
                    nombre_unidad_de_captura,
                    try_cast(subcuenta AS INTEGER) AS subcuenta,
                    nombre_subcuenta,
                    trim(coalesce(nombre_unidad_de_captura, '') || ' | ' || coalesce(nombre_subcuenta, '')) AS concept_name,
                    lower(trim(coalesce(nombre_unidad_de_captura, '') || ' ' || coalesce(nombre_subcuenta, ''))) AS concept_norm,
                    raw_value,
                    try_cast(replace(raw_value, ',', '') AS DOUBLE) AS normalized_value,
                    ingestion_timestamp,
                    source_dataset_id,
                    source_url,
                    raw_file_name,
                    extraction_method
                FROM unpivoted
            ),
            classified AS (
                SELECT
                    *,
                    {mapping_case} AS metric_name
                FROM typed
                WHERE normalized_value IS NOT NULL
                  AND normalized_value <> 0
            )
            SELECT
                period_date,
                year,
                month,
                company_code,
                company_name_raw,
                company_name_clean,
                company_display_name,
                company_name_raw AS company_name,
                company_name_clean AS company_standard,
                ramo_code,
                ramo_name_raw,
                ramo_name_clean,
                ramo_display_name,
                ramo_name_raw AS ramo,
                ramo_name_clean AS ramo_standard,
                unidad_de_captura,
                nombre_unidad_de_captura,
                subcuenta,
                nombre_subcuenta,
                concept_name,
                metric_name,
                CASE WHEN metric_name = 'pending_mapping' THEN 'PENDING_MAPPING' ELSE 'MAPPED' END AS mapping_status,
                raw_value,
                normalized_value,
                'COP' AS currency,
                CASE
                    WHEN unidad_de_captura = 19 THEN 'millones de pesos'
                    WHEN unidad_de_captura = 20 THEN 'unidades'
                    ELSE 'pesos'
                END AS unit,
                ? AS source,
                source_dataset_id,
                source_url,
                raw_file_name,
                extraction_method,
                ingestion_timestamp
            FROM classified
            """,
            [FORMATO_290_SOURCE_NAME],
        )
        logger.info("Creating mapping status and marts")
        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {MAPPING_TABLE} AS
            SELECT metric_name, mapping_status, concept_name, COUNT(*) AS records, SUM(normalized_value) AS total_value
            FROM {CLEAN_TABLE}
            GROUP BY metric_name, mapping_status, concept_name
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_dashboard_metrics AS
            SELECT
                period_date,
                year,
                month,
                company_code,
                company_name,
                company_standard,
                company_display_name,
                ramo,
                ramo_standard,
                ramo_display_name,
                metric_name,
                SUM(normalized_value) AS metric_value,
                'COLOMBIA' AS country,
                'LATIN AMERICA AND CARIBBEAN' AS region,
                'SUPERINTENDENCIA FINANCIERA DE COLOMBIA' AS regulator,
                ? AS source,
                'COP' AS currency,
                ? AS source_file,
                ? AS updated_at
            FROM clean_formato_290
            WHERE mapping_status = 'MAPPED'
            GROUP BY period_date, year, month, company_code, company_name, company_standard, company_display_name, ramo, ramo_standard, ramo_display_name, metric_name
            """,
            [FORMATO_290_SOURCE_NAME, FORMATO_290_DATASET_ID, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_premiums AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('direct_written_premium','accepted_premium','accepted_reinsurance_premium','premium_cancellations','ceded_premium','retained_premium','earned_premium','discounts')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_claims AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('claims_liquidated','claims_reimbursements','recoveries_salvage','claims_incurred')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_commissions AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('commissions','intermediary_charges','intermediary_charges_asset_balance','reinsurance_commissions')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_reinsurance AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('ceded_premium','accepted_reinsurance_premium','reinsurance_ceded_premium','reinsurance_commissions')
            """
        )
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_technical_result AS
            SELECT * FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('technical_result','technical_reserves','administrative_expenses')
            """
        )
        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {FACT_CORE_TABLE} AS
            SELECT
                country,
                region,
                regulator,
                source,
                period_date,
                year,
                month,
                company_name AS company_local,
                company_standard,
                company_display_name,
                ramo AS line_of_business_local,
                ramo_standard AS line_of_business_standard,
                ramo_display_name AS line_of_business_display_name,
                'NACIONAL' AS city,
                'gross_written_premium' AS metric_name,
                SUM(metric_value) AS metric_value,
                currency,
                source_file,
                updated_at
            FROM mart_formato_290_dashboard_metrics
            WHERE metric_name IN ('direct_written_premium','accepted_premium','accepted_reinsurance_premium')
              AND ramo_standard NOT IN ('TOTAL','SUBTOTAL RAMOS')
            GROUP BY country, region, regulator, source, period_date, year, month, company_name, company_standard, company_display_name, ramo, ramo_standard, ramo_display_name, currency, source_file, updated_at
            UNION ALL
            SELECT
                country,
                region,
                regulator,
                source,
                period_date,
                year,
                month,
                company_name AS company_local,
                company_standard,
                company_display_name,
                ramo AS line_of_business_local,
                ramo_standard AS line_of_business_standard,
                ramo_display_name AS line_of_business_display_name,
                'NACIONAL' AS city,
                'claims' AS metric_name,
                SUM(metric_value) AS metric_value,
                currency,
                source_file,
                updated_at
            FROM mart_formato_290_dashboard_metrics
            WHERE metric_name = 'claims_incurred'
              AND ramo_standard NOT IN ('TOTAL','SUBTOTAL RAMOS')
            GROUP BY country, region, regulator, source, period_date, year, month, company_name, company_standard, company_display_name, ramo, ramo_standard, ramo_display_name, currency, source_file, updated_at
            """
        )
        _create_outputs_from_duckdb(conn)
        validation_df = _create_validation_from_duckdb(conn)
        conn.register("validation_df", validation_df)
        conn.execute(f"CREATE OR REPLACE TABLE {VALIDATION_TABLE} AS SELECT * FROM validation_df")
        conn.unregister("validation_df")
        validation_df.to_csv(OUTPUT_VALIDATION_DIR / "formato_290_validation_results.csv", index=False, encoding="utf-8-sig")

        template = pd.DataFrame(
            columns=[
                "metric_name",
                "period",
                "company",
                "ramo",
                "official_value",
                "dashboard_value",
                "difference",
                "percentage_difference",
                "tolerance_absolute",
                "tolerance_percentage",
                "status",
                "comments",
            ]
        )
        template.to_csv(REFERENCE_DIR / "formato_290_reconciliation_template.csv", index=False, encoding="utf-8-sig")

        raw_rows = conn.execute(f"SELECT COUNT(*) FROM {RAW_TABLE}").fetchone()[0]
        clean_rows = conn.execute(f"SELECT COUNT(*) FROM {CLEAN_TABLE}").fetchone()[0]
        dashboard_rows = conn.execute("SELECT COUNT(*) FROM mart_formato_290_dashboard_metrics").fetchone()[0]
        fact_core_rows = conn.execute(f"SELECT COUNT(*) FROM {FACT_CORE_TABLE}").fetchone()[0]
        companies = conn.execute(f"SELECT COUNT(DISTINCT company_standard) FROM {CLEAN_TABLE}").fetchone()[0]
        ramos = conn.execute(f"SELECT COUNT(DISTINCT ramo_standard) FROM {CLEAN_TABLE}").fetchone()[0]
        latest_period = conn.execute(f"SELECT MAX(period_date) FROM {CLEAN_TABLE}").fetchone()[0]
        mapped_metrics = conn.execute(f"SELECT DISTINCT metric_name FROM {CLEAN_TABLE} WHERE mapping_status = 'MAPPED' ORDER BY metric_name").fetchdf()["metric_name"].tolist()
        pending_metrics = conn.execute(f"SELECT DISTINCT metric_name FROM {CLEAN_TABLE} WHERE mapping_status <> 'MAPPED' ORDER BY metric_name").fetchdf()["metric_name"].tolist()
        validation_status = "FAIL" if (validation_df["status"] == "FAIL").any() else "WARNING" if (validation_df["status"] == "WARNING").any() else "PASS"
    finally:
        conn.close()

    status = {
        "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_id": FORMATO_290_DATASET_ID,
        "source_url": FORMATO_290_SOURCE_URL,
        "raw_rows": int(raw_rows),
        "clean_rows": int(clean_rows),
        "dashboard_rows": int(dashboard_rows),
        "fact_core_rows": int(fact_core_rows),
        "companies": int(companies),
        "ramos": int(ramos),
        "latest_period": latest_period.strftime("%Y-%m-%d") if latest_period else "N/A",
        "validation_status": validation_status,
        "raw_file": str(raw_file.relative_to(PROJECT_ROOT)) if raw_file.is_relative_to(PROJECT_ROOT) else str(raw_file),
        "mapped_metrics": mapped_metrics,
        "pending_metrics": pending_metrics,
    }
    pd.DataFrame([status]).to_csv(OUTPUT_VALIDATION_DIR / "formato_290_latest_status.csv", index=False, encoding="utf-8-sig")
    logger.info("Formato 290 processing completed: %s", status)
    return status


def run_update(from_latest_raw: bool = False, raw_file: str | Path | None = None) -> dict[str, object]:
    logger = configure_logging()
    ensure_dirs()
    logger.info("Starting Formato 290 update")

    try:
        if raw_file:
            selected_raw = Path(raw_file)
            if not selected_raw.is_absolute():
                selected_raw = PROJECT_ROOT / selected_raw
            logger.info("Resuming from explicit raw file: %s", selected_raw)
            return process_raw_file(selected_raw, logger, extraction_method="Explicit local raw CSV")
        if from_latest_raw:
            selected_raw = latest_raw_file()
            logger.info("Resuming from latest raw file: %s", selected_raw)
            return process_raw_file(selected_raw, logger, extraction_method="Latest local raw CSV")

        metadata = fetch_metadata()
        logger.info("Verified dataset: %s", metadata.get("name"))
        raw_df = download_all_rows()
        if raw_df.empty:
            raise RuntimeError("Formato 290 download returned zero rows.")
        selected_raw = RAW_DIR / f"formato_290_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        raw_df.to_csv(selected_raw, index=False, encoding="utf-8-sig")
        logger.info("Raw audit file written: %s rows=%s", selected_raw, len(raw_df))
        return process_raw_file(selected_raw, logger, extraction_method="Socrata API pagination")
    except Exception:
        logger.exception("Formato 290 update failed with traceback")
        raise
