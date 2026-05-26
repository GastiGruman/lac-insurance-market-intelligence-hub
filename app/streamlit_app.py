import streamlit as st
import duckdb
import json
import os
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
import unicodedata
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.broker_analytics import (
    annual_summary_csv,
    build_company_brief,
    build_reinsurance_view_context,
    build_reinsurance_wide,
    build_technical_signals,
    company_summary_csv,
    reinsurance_summary_csv,
    render_markdown_as_html,
    render_one_pager_markdown,
    summarize_reinsurance,
)
from src.ai_brief import (
    answer_ai_brief_question,
    answer_ask_data,
    build_ai_brief_context,
    build_structured_ai_context,
    context_to_json,
    generate_ai_brief_from_context,
    generate_ai_brief,
    generate_ai_meeting_prep,
)
from src.ai_utils import get_ai_config
from src.news import (
    ENABLE_LIVE_NEWS,
    build_company_news_context,
    load_curated_company_news,
    load_key_people_template,
)
from src.exports import (
    build_ai_brief_markdown as build_export_ai_brief_markdown,
    build_broker_one_pager_markdown as build_export_broker_one_pager_markdown,
    build_company_brief_markdown as build_export_company_brief_markdown,
    build_export_metadata,
    build_market_summary_markdown as build_export_market_summary_markdown,
    build_ppt_ready_bullets,
    build_reinsurance_summary_markdown as build_export_reinsurance_summary_markdown,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    sanitize_export_filename,
)
from src.ui_components import (
    configure_plotly_theme,
    format_display_dataframe,
    inject_global_css,
    render_empty_state,
    render_metric_card,
    render_section_header,
    render_sidebar_label,
    render_status_pill,
    render_top_header,
)

# ============================================================
# CONFIGURACIÃ“N GENERAL
# ============================================================

st.set_page_config(
    page_title="LAC Insurance Market Intelligence Hub",
    layout="wide"
)

inject_global_css()
configure_plotly_theme()

APP_NAME = "LAC Insurance Market Intelligence Hub"
COUNTRY_MODULE = "Colombia country module"
BUILD_VERSION = "Formato 290 broker analytics v2"
EXPECTED_BRANCH = "demo-streamlit-cloud"
EXPECTED_COMMIT_MARKER = "0344ed9"
UI_MARKER = "month-cutoff-comparison-mode"
USE_CANDIDATE_DB = os.getenv("USE_CANDIDATE_DB", "false").strip().lower() in {"1", "true", "yes", "y"}
CLOUD_DB_PATH = Path("data/database/insurance_market_cloud.duckdb")
CANDIDATE_DB_PATH = Path("data/database/insurance_market_candidate.duckdb")
DEFAULT_DB_PATH = Path("data/database/insurance_market.duckdb")
IS_STREAMLIT_CLOUD = (
    bool(os.getenv("STREAMLIT_SHARING_MODE"))
    or bool(os.getenv("STREAMLIT_CLOUD"))
    or Path("/mount/src").exists()
    or os.getenv("HOME", "").replace("\\", "/").startswith("/home/appuser")
)
USE_CLOUD_DB = os.getenv("USE_CLOUD_DB", "false").strip().lower() in {"1", "true", "yes", "y"}
if USE_CANDIDATE_DB:
    DB_PATH = CANDIDATE_DB_PATH
elif CLOUD_DB_PATH.exists() and (IS_STREAMLIT_CLOUD or USE_CLOUD_DB):
    DB_PATH = CLOUD_DB_PATH
else:
    DB_PATH = DEFAULT_DB_PATH
DB_MODE_LABEL = (
    "candidate local test"
    if DB_PATH == CANDIDATE_DB_PATH
    else "cloud compact"
    if DB_PATH == CLOUD_DB_PATH
    else "stable full local"
)
VALIDATION_REPORT_PATH = Path("outputs/market_core_validation_report.csv")
INDICADORES_VALIDATION_REPORT_PATH = Path("outputs/indicadores_gestion_2025_validation_report.csv")
INDICADORES_VALIDATION_FLAGS_PATH = Path("outputs/indicadores_gestion_2025_flags.csv")
PIPELINE_STATUS_PATH = Path("data/metadata/latest_pipeline_status.json")
COMPANY_ALIASES_PATH = Path("config/company_aliases.csv")
CORE_MARKET_SOURCE = "FASECOLDA - CIUDADES Y RAMOS"
CORE_SOURCE_VALUE_MULTIPLIER = 1_000
DEBUG_MODE = os.getenv("APP_DEBUG_MODE", "false").strip().lower() in {"1", "true", "yes", "y"}
CLAIMS_PREMIUM_RATIO_LABEL_ES = "Siniestros incurridos / prima escrita"
CLAIMS_PREMIUM_RATIO_LABEL_EN = "Incurred Claims / Written Premium"
CLAIMS_PREMIUM_RATIO_NOTE = (
    "The default claims ratio is an analytical technical movement ratio calculated as "
    "mapped incurred claims over mapped written premium in the app database. It is not "
    "a conventional gross loss ratio, official technical siniestralidad, or combined "
    "ratio. Negative values may reflect reserve, recovery, net technical account or "
    "source-mapping movements and require business validation."
)
CLAIMS_PREMIUM_RATIO_NOTE_ES = (
    "El ratio por defecto corresponde a una metrica tecnica analitica calculada como "
    "siniestros incurridos mapeados sobre prima escrita mapeada en la base de la app. "
    "No es una siniestralidad bruta convencional, siniestralidad tecnica oficial ni "
    "indice combinado. Valores negativos pueden reflejar movimientos de reservas, "
    "recobros, efectos netos o mapeos pendientes y requieren validacion de negocio."
)

MONTH_NAME = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}
MONTH_ABBR = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

# ============================================================
# FUNCIONES DE CARGA
# ============================================================

@st.cache_data
def get_core_market_table_name():
    if not DB_PATH.exists():
        return None
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = set(
            conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchdf()["table_name"].tolist()
        )
        if "fact_market_core_formato_290" in tables:
            return "fact_market_core_formato_290"
        if "fact_market_core" in tables:
            return "fact_market_core"
        return None
    finally:
        conn.close()


@st.cache_data
def load_market_core():
    if not DB_PATH.exists():
        return pd.DataFrame()

    core_table = get_core_market_table_name()
    if not core_table:
        return pd.DataFrame()

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if core_table == "fact_market_core_formato_290":
            return conn.execute(f"""
                SELECT *
                FROM {core_table}
            """).fetchdf()
        return conn.execute(f"""
            WITH latest_months AS (
                SELECT country, source, year, MAX(month) AS month
                FROM {core_table}
                GROUP BY country, source, year
            )
            SELECT f.*
            FROM {core_table} f
            INNER JOIN latest_months lm
                ON f.country = lm.country
               AND f.source = lm.source
               AND f.year = lm.year
               AND f.month = lm.month
        """).fetchdf()
    finally:
        conn.close()


@st.cache_data
def load_market_core_all_periods():
    if not DB_PATH.exists():
        return pd.DataFrame()

    core_table = get_core_market_table_name()
    if not core_table:
        return pd.DataFrame()

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return conn.execute(f"""
            SELECT *
            FROM {core_table}
        """).fetchdf()
    finally:
        conn.close()


@st.cache_data
def load_validation_report():
    if VALIDATION_REPORT_PATH.exists():
        return pd.read_csv(VALIDATION_REPORT_PATH)
    return pd.DataFrame(columns=["test_name", "result", "detail"])


@st.cache_data
def load_indicadores_gestion_2025():
    try:
        if not DB_PATH.exists():
            return pd.DataFrame()

        conn = duckdb.connect(str(DB_PATH), read_only=True)
        try:
            return conn.execute("""
                SELECT *
                FROM fact_indicadores_gestion_2025
            """).fetchdf()
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_indicadores_gestion_validation():
    if INDICADORES_VALIDATION_REPORT_PATH.exists():
        return pd.read_csv(INDICADORES_VALIDATION_REPORT_PATH)
    return pd.DataFrame(columns=["test_name", "result", "detail"])


@st.cache_data
def load_indicadores_gestion_validation_flags():
    if INDICADORES_VALIDATION_FLAGS_PATH.exists():
        return pd.read_csv(INDICADORES_VALIDATION_FLAGS_PATH)
    return pd.DataFrame(
        columns=[
            "flag_name",
            "severity",
            "country",
            "year",
            "company_standard",
            "line_of_business_standard",
            "detail",
        ]
    )


@st.cache_data
def load_lob_mapping():
    try:
        if not DB_PATH.exists():
            return pd.DataFrame()

        conn = duckdb.connect(str(DB_PATH), read_only=True)
        try:
            return conn.execute("""
                SELECT *
                FROM dim_line_of_business_mapping
            """).fetchdf()
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_company_mapping():
    try:
        if not DB_PATH.exists():
            return pd.DataFrame()

        conn = duckdb.connect(str(DB_PATH), read_only=True)
        try:
            return conn.execute("""
                SELECT *
                FROM dim_company_mapping
            """).fetchdf()
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_pipeline_status():
    if not PIPELINE_STATUS_PATH.exists():
        return {}
    try:
        return json.loads(PIPELINE_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data
def load_formato_290_status():
    if not DB_PATH.exists():
        return {}
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = set(
            conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchdf()["table_name"].tolist()
        )
        if "clean_formato_290" in tables:
            latest = conn.execute("SELECT MAX(period_date) FROM clean_formato_290").fetchone()[0]
            rows = conn.execute("SELECT COUNT(*) FROM clean_formato_290").fetchone()[0]
            companies = conn.execute("SELECT COUNT(DISTINCT company_standard) FROM clean_formato_290").fetchone()[0]
            ramos = conn.execute("SELECT COUNT(DISTINCT ramo_standard) FROM clean_formato_290").fetchone()[0]
            raw_rows = conn.execute("SELECT COUNT(*) FROM raw_formato_290").fetchone()[0] if "raw_formato_290" in tables else None
            fact_rows = conn.execute("SELECT COUNT(*) FROM fact_market_core_formato_290").fetchone()[0] if "fact_market_core_formato_290" in tables else None
            ingestion = None
            extraction_method = None
            database_mode = DB_MODE_LABEL
            if "raw_formato_290" in tables:
                ingestion = conn.execute("SELECT MAX(ingestion_timestamp) FROM raw_formato_290").fetchone()[0]
                extraction_method = conn.execute("SELECT MAX(extraction_method) FROM raw_formato_290").fetchone()[0]
        elif "formato_290_cloud_metadata" in tables:
            metadata = conn.execute("SELECT * FROM formato_290_cloud_metadata LIMIT 1").fetchdf()
            row = metadata.iloc[0].to_dict() if not metadata.empty else {}
            latest = row.get("latest_period")
            rows = row.get("clean_rows")
            companies = row.get("companies")
            ramos = row.get("ramos")
            raw_rows = row.get("raw_rows")
            fact_rows = row.get("fact_rows")
            ingestion = row.get("ingestion_timestamp")
            extraction_method = row.get("extraction_method")
            database_mode = row.get("database_mode") or DB_MODE_LABEL
        elif "fact_market_core_formato_290" in tables:
            latest = conn.execute("SELECT MAX(period_date) FROM fact_market_core_formato_290").fetchone()[0]
            rows = None
            companies = conn.execute("SELECT COUNT(DISTINCT company_standard) FROM fact_market_core_formato_290").fetchone()[0]
            ramos = conn.execute("SELECT COUNT(DISTINCT line_of_business_standard) FROM fact_market_core_formato_290").fetchone()[0]
            raw_rows = None
            fact_rows = conn.execute("SELECT COUNT(*) FROM fact_market_core_formato_290").fetchone()[0]
            ingestion = None
            extraction_method = "compact fact fallback"
            database_mode = DB_MODE_LABEL
        else:
            return {"available": False}
        validation_status = "Not validated"
        validation_counts = {}
        if "validation_formato_290" in tables:
            validation_counts_df = conn.execute(
                "SELECT status, COUNT(*) AS count FROM validation_formato_290 GROUP BY status"
            ).fetchdf()
            validation_counts = dict(zip(validation_counts_df["status"], validation_counts_df["count"]))
            statuses = validation_counts_df["status"].tolist()
            validation_status = "FAIL" if "FAIL" in statuses else "WARNING" if "WARNING" in statuses else "PASS"
        mapped_metrics = []
        pending_metrics = []
        if "formato_290_metric_mapping_status" in tables:
            mapping_df = conn.execute(
                """
                SELECT metric_name, mapping_status, COUNT(*) AS records
                FROM formato_290_metric_mapping_status
                GROUP BY metric_name, mapping_status
                ORDER BY metric_name
                """
            ).fetchdf()
            mapped_metrics = sorted(mapping_df.loc[mapping_df["mapping_status"] == "MAPPED", "metric_name"].dropna().unique().tolist())
            pending_metrics = sorted(mapping_df.loc[mapping_df["mapping_status"] != "MAPPED", "metric_name"].dropna().unique().tolist())
        return {
            "available": True,
            "latest_period": latest,
            "rows": rows,
            "raw_rows": raw_rows,
            "fact_rows": fact_rows,
            "companies": companies,
            "ramos": ramos,
            "ingestion_timestamp": ingestion,
            "extraction_method": extraction_method,
            "database_mode": database_mode,
            "database_path": str(DB_PATH),
            "validation_status": validation_status,
            "validation_counts": validation_counts,
            "mapped_metrics": mapped_metrics,
            "pending_metrics": pending_metrics,
        }
    finally:
        conn.close()


@st.cache_data
def load_metric_readiness_matrix():
    path = Path("outputs/data_quality/formato_290_metric_readiness_matrix.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_combined_ratio_readiness():
    path = Path("outputs/data_quality/formato_290_combined_ratio_readiness.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_technical_bridge_summary():
    path = Path("outputs/data_quality/formato_290_technical_bridge_summary.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_company_aliases():
    if not COMPANY_ALIASES_PATH.exists():
        return pd.DataFrame(
            columns=[
                "company_code",
                "company_name_clean",
                "company_short_name",
                "company_group_name",
                "active",
            ]
        )
    try:
        aliases = pd.read_csv(COMPANY_ALIASES_PATH)
        aliases["company_code"] = aliases["company_code"].astype(str).str.strip()
        aliases["company_name_clean"] = aliases["company_name_clean"].astype(str).str.strip().str.upper()
        aliases["company_short_name"] = aliases["company_short_name"].astype(str).str.strip()
        aliases["company_group_name"] = aliases["company_group_name"].astype(str).str.strip()
        aliases["active"] = aliases["active"].astype(str).str.upper().isin(["TRUE", "1", "YES", "Y"])
        return aliases[aliases["active"]].copy()
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_formato_290_technical_bridge():
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = set(
            conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchdf()["table_name"].tolist()
        )
        if "mart_formato_290_technical_bridge" not in tables:
            return pd.DataFrame()
        return conn.execute("SELECT * FROM mart_formato_290_technical_bridge").fetchdf()
    finally:
        conn.close()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def format_millions(value):
    if pd.isna(value):
        return "N/A"
    return f"COP {value / 1_000_000:,.0f} MM"


def format_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def format_percentage(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def render_section_error(error):
    st.error("This section could not be loaded. Please adjust the filters or try again.")
    if DEBUG_MODE:
        st.exception(error)


def render_dataframe(data, **kwargs):
    st.dataframe(format_display_dataframe(data), **kwargs)


def warn_and_stop(message):
    st.warning(message)
    st.stop()


def safe_has_columns(data, required_columns):
    return isinstance(data, pd.DataFrame) and set(required_columns).issubset(data.columns)


def safe_divide(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return None
    return numerator / denominator


def extract_company_code(value):
    text = str(value or "").strip()
    if "|" in text:
        return text.split("|", 1)[0].strip()
    first_token = text.split(" ", 1)[0].strip()
    return first_token if "-" in first_token else ""


def apply_company_aliases(data, aliases):
    enriched = data.copy()
    if enriched.empty:
        return enriched

    if "company_code" not in enriched.columns:
        if "company_display_name" in enriched.columns:
            enriched["company_code"] = enriched["company_display_name"].map(extract_company_code)
        elif "company_local" in enriched.columns:
            enriched["company_code"] = enriched["company_local"].map(extract_company_code)
        else:
            enriched["company_code"] = ""

    if "company_name_clean" not in enriched.columns:
        source_name_col = "company_standard" if "company_standard" in enriched.columns else "company_display_name"
        enriched["company_name_clean"] = enriched.get(source_name_col, pd.Series(dtype=str)).astype(str).str.strip().str.upper()

    if "company_display_name" not in enriched.columns:
        enriched["company_display_name"] = (
            enriched["company_code"].astype(str).str.strip()
            + " | "
            + enriched["company_name_clean"].astype(str).str.strip()
        ).str.strip(" |")

    if aliases is not None and not aliases.empty:
        alias_cols = ["company_code", "company_name_clean", "company_short_name", "company_group_name"]
        enriched = enriched.merge(
            aliases[alias_cols].drop_duplicates(),
            on=["company_code", "company_name_clean"],
            how="left",
        )
    else:
        enriched["company_short_name"] = pd.NA
        enriched["company_group_name"] = pd.NA

    enriched["company_short_name"] = (
        enriched["company_short_name"]
        .fillna(enriched["company_name_clean"])
        .astype(str)
        .str.replace(r"\s+S\.A\.?$", "", regex=True)
        .str.strip()
    )
    enriched["company_group_name"] = enriched["company_group_name"].fillna(enriched["company_short_name"])
    return enriched


def clean_ramo_label(value):
    text = str(value or "").strip()
    text = text.replace("_mes", "").replace("_MES", "")
    text = text.replace(" MES", "").replace(" mes", "")
    return " ".join(text.upper().split())


AGGREGATE_LINE_KEYWORDS = (
    "TOTAL",
    "SUBTOTAL",
    "TOTAL RAMOS",
    "SUBTOTAL RAMOS",
    "OPE NO RAMOS",
    "OPERACIONES NO RAMOS",
)


def is_real_line_of_business(value):
    label = clean_ramo_label(value)
    if not label:
        return False
    return not any(keyword in label for keyword in AGGREGATE_LINE_KEYWORDS)


def filter_real_lob_rows(data):
    filtered = data.copy()
    if filtered.empty:
        return filtered
    line_col = None
    for candidate in ["line_of_business_standard", "ramo_name_clean", "ramo_display_name"]:
        if candidate in filtered.columns:
            line_col = candidate
            break
    if not line_col:
        return filtered
    return filtered[filtered[line_col].map(is_real_line_of_business)].copy()


def apply_line_labels(data):
    enriched = data.copy()
    if enriched.empty:
        return enriched
    if "line_of_business_standard" in enriched.columns:
        enriched["line_of_business_standard"] = enriched["line_of_business_standard"].map(clean_ramo_label)
    if "line_of_business_display_name" in enriched.columns:
        enriched["line_of_business_display_name"] = enriched["line_of_business_display_name"].map(clean_ramo_label)
    if "ramo_name_clean" in enriched.columns:
        enriched["ramo_name_clean"] = enriched["ramo_name_clean"].map(clean_ramo_label)
    if "ramo_display_name" in enriched.columns:
        enriched["ramo_display_name"] = enriched["ramo_display_name"].map(clean_ramo_label)
    return enriched


def get_company_display(data):
    if "company_display_name" in data.columns:
        return data["company_display_name"]
    if "company_standard" in data.columns:
        return data["company_standard"]
    return pd.Series(dtype=str)


def prepare_bridge_scope(bridge_df, selected_years_scope, month_cutoff, company="TODAS", line="TODOS"):
    if bridge_df.empty:
        return bridge_df.copy()
    bridge = bridge_df.copy()
    bridge["year"] = pd.to_numeric(bridge["year"], errors="coerce").astype("Int64")
    bridge["month"] = pd.to_numeric(bridge["month"], errors="coerce").astype("Int64")
    bridge = bridge[bridge["year"].isin([int(year) for year in selected_years_scope])]
    if comparison_mode == "Full year vs previous full year":
        bridge = bridge[bridge["month"] == 12]
    else:
        bridge = bridge[bridge["month"] == int(month_cutoff)]
    if company != "TODAS":
        bridge = bridge[bridge["company_name_clean"] == company]
    if line != "TODOS":
        bridge = bridge[bridge["ramo_name_clean"] == line]
    return bridge.copy()


def summarize_bridge(data, group_cols):
    if data.empty:
        return pd.DataFrame(columns=group_cols)
    if not group_cols:
        written = data["written_premium_dashboard_basis"].sum() if "written_premium_dashboard_basis" in data.columns else None
        ceded = data["ceded_premium_display_abs"].sum() if "ceded_premium_display_abs" in data.columns else None
        retained = data["retained_premium"].sum() if "retained_premium" in data.columns else None
        technical = data["official_technical_result_raw"].sum() if "official_technical_result_raw" in data.columns else None
        return pd.DataFrame([{
            "written_premium": written,
            "ceded_premium": ceded,
            "retained_premium": retained,
            "technical_result": technical,
            "cession_ratio": safe_divide(ceded, written),
            "retention_ratio": safe_divide(retained, written),
            "technical_result_ratio": safe_divide(technical, written),
        }])
    summary = (
        data
        .groupby(group_cols, dropna=False, as_index=False)
        .agg(
            written_premium=("written_premium_dashboard_basis", "sum"),
            ceded_premium=("ceded_premium_display_abs", "sum"),
            retained_premium=("retained_premium", "sum"),
            technical_result=("official_technical_result_raw", "sum"),
        )
    )
    summary["cession_ratio"] = summary.apply(lambda row: safe_divide(row["ceded_premium"], row["written_premium"]), axis=1)
    summary["retention_ratio"] = summary.apply(lambda row: safe_divide(row["retained_premium"], row["written_premium"]), axis=1)
    summary["technical_result_ratio"] = summary.apply(lambda row: safe_divide(row["technical_result"], row["written_premium"]), axis=1)
    return summary


def normalize_core_market_units(data):
    """
    Fasecolda Ciudades y Ramos publishes VALOR in thousands of COP.
    The app stores the extracted value and converts it to COP for analytics.
    """
    normalized = data.copy()
    if "source" not in normalized.columns or "metric_value" not in normalized.columns:
        return normalized

    source_mask = (
        normalized["source"]
        .astype(str)
        .str.upper()
        .str.strip()
        .eq(CORE_MARKET_SOURCE)
    )
    normalized.loc[source_mask, "metric_value"] = (
        normalized.loc[source_mask, "metric_value"] * CORE_SOURCE_VALUE_MULTIPLIER
    )
    return normalized


def apply_formato_290_period_mode(data, selected_years_scope, month_cutoff, comparison_mode):
    filtered = data.copy()
    if filtered.empty:
        return filtered
    filtered["year"] = pd.to_numeric(filtered["year"], errors="coerce").astype("Int64")
    filtered["month"] = pd.to_numeric(filtered["month"], errors="coerce").astype("Int64")
    selected_years_scope = [int(year) for year in selected_years_scope]
    month_cutoff = int(month_cutoff)

    if comparison_mode == "Full year vs previous full year":
        return filtered[(filtered["year"].isin(selected_years_scope)) & (filtered["month"] == 12)].copy()

    if comparison_mode == "Selected month vs same month previous year":
        key_cols = [
            col for col in [
                "country",
                "region",
                "regulator",
                "source",
                "year",
                "company_local",
                "company_standard",
                "company_display_name",
                "line_of_business_local",
                "line_of_business_standard",
                "line_of_business_display_name",
                "city",
                "metric_name",
                "currency",
                "source_file",
                "updated_at",
            ]
            if col in filtered.columns
        ]
        current = filtered[(filtered["year"].isin(selected_years_scope)) & (filtered["month"] == month_cutoff)].copy()
        if month_cutoff > 1:
            prior_month = filtered[(filtered["year"].isin(selected_years_scope)) & (filtered["month"] == month_cutoff - 1)].copy()
            prior_cols = key_cols + ["metric_value"]
            prior_month = prior_month[prior_cols].rename(columns={"metric_value": "prior_month_value"})
            current = current.merge(prior_month, on=key_cols, how="left")
            current["metric_value"] = current["metric_value"] - current["prior_month_value"].fillna(0)
            current = current.drop(columns=["prior_month_value"])
        current["period_date"] = pd.to_datetime(
            {
                "year": current["year"].astype(int),
                "month": current["month"].astype(int),
                "day": 1,
            },
            errors="coerce",
        )
        return current

    return filtered[(filtered["year"].isin(selected_years_scope)) & (filtered["month"] == month_cutoff)].copy()


def latest_market_snapshot_by_year(data):
    """
    Ciudades y Ramos monthly files are cumulative cuts. Annual analysis should
    use the latest available month in each year instead of summing all cuts.
    """
    if data.empty or not {"country", "source", "year", "month"}.issubset(data.columns):
        return data.copy()

    snapshot = data.copy()
    snapshot["month"] = pd.to_numeric(snapshot["month"], errors="coerce")
    latest_month = snapshot.groupby(["country", "source", "year"])["month"].transform("max")
    return snapshot[snapshot["month"].eq(latest_month)].copy()


def fix_year_axis(fig, years):
    years = sorted(pd.Series(years).dropna().astype(int).unique())
    tick_labels = [format_period_year_label(year) for year in years]
    fig.update_xaxes(
        tickmode="array",
        tickvals=years,
        ticktext=tick_labels,
        tickformat="d"
    )
    return fig


def format_period_year_label(year):
    try:
        year = int(year)
    except Exception:
        return str(year)
    if not globals().get("is_formato_290_core", False):
        return str(year)

    month = int(globals().get("selected_month_cutoff") or 12)
    mode = globals().get("comparison_mode", "")
    month_text = MONTH_ABBR.get(month, str(month))
    if mode == "YTD vs same period previous year":
        return f"{year} YTD {month_text}"
    if mode == "Selected month vs same month previous year":
        return f"{month_text} {year}"
    if mode == "Full year vs previous full year":
        return str(year)
    if month < 12:
        return f"{year} as of {month_text}"
    return str(year)


def normalize_lob_text(value):
    if value is None:
        return ""
    return str(value).strip().upper()


def normalize_match_text(value):
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def get_aggregate_lob_lookup(country="COLOMBIA", target_source="FASECOLDA - INDICADORES DE GESTION"):
    aggregate_names = {
        "TOTAL DANOS",
        "TOTAL DAÃ‘OS",
        "TOTAL PERSONAS",
        "TOTAL SEGURIDAD SOCIAL",
    }

    if "lob_mapping_df" not in globals() or lob_mapping_df.empty:
        return {normalize_match_text(value) for value in aggregate_names}

    mapping = lob_mapping_df.copy()

    required_cols = {
        "country",
        "source",
        "source_line_of_business",
        "standard_line_of_business",
        "lob_group",
    }

    if not required_cols.issubset(mapping.columns):
        return {normalize_match_text(value) for value in aggregate_names}

    mapping["country_norm"] = mapping["country"].map(normalize_match_text)
    mapping["source_norm"] = mapping["source"].map(normalize_match_text)
    mapping["lob_group_norm"] = mapping["lob_group"].map(normalize_match_text)

    aggregate_mapping = mapping[
        (mapping["country_norm"] == normalize_match_text(country)) &
        (mapping["lob_group_norm"] == "AGGREGATE")
    ]

    for _, row in aggregate_mapping.iterrows():
        aggregate_names.add(row.get("source_line_of_business", ""))
        aggregate_names.add(row.get("standard_line_of_business", ""))

    return {normalize_match_text(value) for value in aggregate_names if str(value).strip()}


def build_mapping_status_summary(lob_mapping, company_mapping):
    lob_rows = len(lob_mapping) if isinstance(lob_mapping, pd.DataFrame) else 0
    company_rows = len(company_mapping) if isinstance(company_mapping, pd.DataFrame) else 0

    countries = set()
    sources = set()

    if lob_rows and "country" in lob_mapping.columns:
        countries.update(lob_mapping["country"].dropna().astype(str).str.strip().unique())
    if company_rows and "country" in company_mapping.columns:
        countries.update(company_mapping["country"].dropna().astype(str).str.strip().unique())

    if lob_rows and "source" in lob_mapping.columns:
        sources.update(lob_mapping["source"].dropna().astype(str).str.strip().unique())
    if company_rows and "source" in company_mapping.columns:
        sources.update(company_mapping["source"].dropna().astype(str).str.strip().unique())

    standard_lobs = (
        lob_mapping["standard_line_of_business"].nunique()
        if lob_rows and "standard_line_of_business" in lob_mapping.columns
        else 0
    )
    standard_companies = (
        company_mapping["standard_company"].nunique()
        if company_rows and "standard_company" in company_mapping.columns
        else 0
    )

    return {
        "lob_rows": lob_rows,
        "company_rows": company_rows,
        "countries": len(countries),
        "sources": len(sources),
        "standard_lobs": standard_lobs,
        "standard_companies": standard_companies,
    }


def map_lob_to_indicadores_gestion(selected_line):
    """
    DEPRECATED: kept only for reference/backward compatibility.

    Reinsurance View now uses dim_line_of_business_mapping through
    map_lob_using_mapping_table(). Do not add new mappings here.
    """

    if selected_line == "TODOS":
        return None

    mapping = {
        "AUTOMOVILES": "Autos",
        "AUTOS": "Autos",
        "INCENDIO Y LUCRO CESANTE": "Incendio y Lucro",
        "INCENDIO Y LUCRO": "Incendio y Lucro",
        "CUMPLIMIENTO": "Cumplimiento",
        "TRANSPORTE": "Transporte",
        "RESPONSABILIDAD CIVIL": "Responsabilidad Civil",
        "TERREMOTO": "Terremoto",
        "VIDA GRUPO": "Vida grupo",
        "VIDA INDIVIDUAL": "Vida individual",
        "SALUD": "Salud",
        "RIESGOS LABORALES": "Riesgos Laborales",
        "SOAT": "Soat",
        "HOGAR": "Hogar",
        "AVIACION": "Aviación",
        "AVIACIÓN": "Aviación",
        "AGROPECUARIO": "Agropecuario",
        "SUSTRACCIÓN": "Sustracción",
        "SUSTRACCIÃ“N": "Sustracción",
        "DESEMPLEO": "Desempleo",
        "EXEQUIAS": "Exequias",
        "MANEJO": "Manejo",
        "CORRIENTE DÉBIL": "Corriente Débil",
        "CORRIENTE DÃ‰BIL": "Corriente Débil",
        "SEGUROS DE CRÉDITO": "Seguros de Credito",
        "SEGUROS DE CRÃ‰DITO": "Seguros de Credito",
        "MINAS Y PETRÓLEOS": "Minas y Petróleos",
        "MINAS Y PETRÃ“LEOS": "Minas y Petróleos",
        "MONTAJE Y ROTURA": "Montaje y Rotura",
        "INGENIERÍA": "Ingenieria",
        "INGENIERÍA": "Ingenieria",
        "TODO RIESGO CONTRATISTA": "Todo Riesgo Cont.",
        "NAVEGACIÓN Y CASCO": "Nav.yCasco",
        "NAVEGACIÃ“N Y CASCO": "Nav.yCasco",
        "VIDRIOS": "Vidrios",
        "DECENAL": "Decenal",
        "BEPS": "BEPS",
        "ACCIDENTES PERSONALES": "Accidentes P",
        "OTROS DAÑOS": "Otros Daños",
        "OTROS DAÃ‘OS": "Otros Daños",
        "OTROS PERSONAS": "Otros Personas",
    }

    normalized = normalize_lob_text(selected_line)
    return mapping.get(normalized)


def prepare_premium_claims_summary(data, group_cols):
    premiums = (
        data[data["metric_name"] == "gross_written_premium"]
        .groupby(group_cols, as_index=False)["metric_value"]
        .sum()
        .rename(columns={"metric_value": "primas"})
    )

    claims = (
        data[data["metric_name"] == "claims"]
        .groupby(group_cols, as_index=False)["metric_value"]
        .sum()
        .rename(columns={"metric_value": "siniestros"})
    )

    summary = premiums.merge(
        claims,
        on=group_cols,
        how="left"
    )

    summary["siniestros"] = summary["siniestros"].fillna(0).abs()
    summary["siniestralidad"] = summary["siniestros"] / summary["primas"]

    return summary


def make_display_summary(summary_df):
    display_df = summary_df.copy()

    if "year" in display_df.columns:
        display_df["year"] = display_df["year"].map(format_period_year_label)

    if "primas" in display_df.columns:
        display_df["primas"] = display_df["primas"].map(format_millions)

    if "siniestros" in display_df.columns:
        display_df["siniestros"] = display_df["siniestros"].map(format_millions)

    if "siniestralidad" in display_df.columns:
        display_df["siniestralidad"] = display_df["siniestralidad"].map(format_percentage)

    if "premium_growth" in display_df.columns:
        display_df["premium_growth"] = display_df["premium_growth"].map(format_percentage)

    if "market_share" in display_df.columns:
        display_df["market_share"] = display_df["market_share"].map(format_percentage)

    display_df = display_df.rename(columns={"siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES})
    return display_df


def generate_structured_company_brief(company_name, company_df, market_df):
    company_summary = prepare_premium_claims_summary(company_df, ["year"])
    market_summary = prepare_premium_claims_summary(market_df, ["year"])

    if company_summary.empty:
        return {
            "executive_summary": "No hay información suficiente para generar el brief.",
            "key_points": [],
            "questions": []
        }

    latest_year = int(company_summary["year"].max())
    previous_year = latest_year - 1

    latest_company = company_summary[company_summary["year"] == latest_year]
    previous_company = company_summary[company_summary["year"] == previous_year]

    latest_market = market_summary[market_summary["year"] == latest_year]

    latest_premium = latest_company["primas"].sum()
    latest_claims = latest_company["siniestros"].sum()
    latest_lr = latest_claims / latest_premium if latest_premium else None

    previous_premium = previous_company["primas"].sum() if not previous_company.empty else None
    premium_growth = (
        (latest_premium / previous_premium - 1)
        if previous_premium and previous_premium != 0
        else None
    )

    market_premium = latest_market["primas"].sum() if not latest_market.empty else None
    market_share = (
        latest_premium / market_premium
        if market_premium and market_premium != 0
        else None
    )

    company_premium = company_df[company_df["metric_name"] == "gross_written_premium"]

    top_lines = (
        company_premium[company_premium["year"] == latest_year]
        .groupby("line_of_business_standard", as_index=False)["metric_value"]
        .sum()
        .sort_values("metric_value", ascending=False)
        .head(5)
    )

    top_lines_text = ", ".join(top_lines["line_of_business_standard"].tolist()) if not top_lines.empty else "N/A"

    executive_summary = (
        f"{company_name} registró primas por {format_millions(latest_premium)} en {latest_year}, "
        f"con siniestros por {format_millions(latest_claims)} y un ratio siniestros / primas de "
        f"{format_percentage(latest_lr)}. "
    )

    if premium_growth is not None:
        executive_summary += (
            f"El crecimiento de primas frente al año anterior fue de "
            f"{format_percentage(premium_growth)}. "
        )

    if market_share is not None:
        executive_summary += (
            f"Su participación estimada sobre el mercado filtrado fue de "
            f"{format_percentage(market_share)}. "
        )

    executive_summary += (
        f"Los principales ramos por primas en el último año disponible fueron: {top_lines_text}."
    )

    key_points = [
        f"Primas último año disponible: {format_millions(latest_premium)}.",
        f"Siniestros último año disponible: {format_millions(latest_claims)}.",
        f"Ratio siniestros / primas último año disponible: {format_percentage(latest_lr)}.",
        f"Crecimiento de primas vs año anterior: {format_percentage(premium_growth)}.",
        f"Market share estimado sobre mercado filtrado: {format_percentage(market_share)}.",
        f"Principales ramos: {top_lines_text}."
    ]

    questions = [
        f"¿Qué está explicando la evolución reciente de primas de {company_name}?",
        f"¿Hay algún ramo donde el ratio siniestros / primas de {company_name} está generando presión técnica?",
        "¿La estrategia de crecimiento está acompañada por ajustes de pricing, retención o selección de riesgos?",
        "¿Existen oportunidades para revisar estructura de reaseguro, límites, deducibles o acumulaciones?",
        "¿Qué apoyo de análisis, benchmarking o market intelligence podría aportar el broker?"
    ]

    return {
        "executive_summary": executive_summary,
        "key_points": key_points,
        "questions": questions
    }




def map_lob_using_mapping_table(selected_line, target_source, country="COLOMBIA"):
    """
    Busca el ramo seleccionado en dim_line_of_business_mapping y devuelve
    el nombre equivalente para la fuente objetivo.

    Ejemplo:
    selected_line = "INCENDIO Y LUCRO CESANTE"
    target_source = "FASECOLDA - INDICADORES DE GESTION"
    devuelve "Incendio y Lucro"
    """

    if selected_line == "TODOS":
        return None

    if "lob_mapping_df" not in globals() or lob_mapping_df.empty:
        return None

    mapping = lob_mapping_df.copy()

    mapping["country_norm"] = mapping["country"].astype(str).str.strip().str.upper()
    mapping["source_norm"] = mapping["source"].astype(str).str.strip().str.upper()
    mapping["source_line_of_business_norm"] = (
        mapping["source_line_of_business"].astype(str).str.strip().str.upper()
    )
    mapping["standard_line_of_business_norm"] = (
        mapping["standard_line_of_business"].astype(str).str.strip().str.upper()
    )

    selected_norm = str(selected_line).strip().upper()
    target_source_norm = str(target_source).strip().upper()
    country_norm = str(country).strip().upper()

    # Primero buscamos cuál es el estándar del ramo seleccionado,
    # sin importar desde qué fuente vino.
    standard_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (
            (mapping["source_line_of_business_norm"] == selected_norm) |
            (mapping["standard_line_of_business_norm"] == selected_norm)
        )
    ]

    if standard_matches.empty:
        return None

    standard_lob = standard_matches.iloc[0]["standard_line_of_business_norm"]

    # Luego buscamos cómo se llama ese estándar en la fuente objetivo.
    target_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["standard_line_of_business_norm"] == standard_lob)
    ]

    if target_matches.empty:
        return None

    return target_matches.iloc[0]["source_line_of_business"]



def map_company_using_mapping_table(selected_company, target_source, country="COLOMBIA"):
    """
    Busca la compañía seleccionada en dim_company_mapping y devuelve
    el nombre equivalente para la fuente objetivo.
    """

    if selected_company == "TODAS":
        return None

    if "company_mapping_df" not in globals() or company_mapping_df.empty:
        return None

    mapping = company_mapping_df.copy()

    mapping["country_norm"] = mapping["country"].astype(str).str.strip().str.upper()
    mapping["source_norm"] = mapping["source"].astype(str).str.strip().str.upper()
    mapping["source_company_norm"] = mapping["source_company"].astype(str).str.strip().str.upper()
    mapping["standard_company_norm"] = mapping["standard_company"].astype(str).str.strip().str.upper()
    mapping["group_name_norm"] = mapping["group_name"].astype(str).str.strip().str.upper()

    selected_norm = str(selected_company).strip().upper()
    target_source_norm = str(target_source).strip().upper()
    country_norm = str(country).strip().upper()

    matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (
            (mapping["source_company_norm"] == selected_norm) |
            (mapping["standard_company_norm"] == selected_norm) |
            (mapping["group_name_norm"] == selected_norm)
        )
    ]

    if matches.empty:
        return None

    standard_company = matches.iloc[0]["standard_company_norm"]
    group_name = matches.iloc[0]["group_name_norm"]

    target_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["standard_company_norm"] == standard_company)
    ]

    if not target_matches.empty:
        return target_matches.iloc[0]["source_company"]

    target_group_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["group_name_norm"] == group_name)
    ]

    if not target_group_matches.empty:
        return target_group_matches.iloc[0]["source_company"]

    return None

# ============================================================
# CARGA Y NORMALIZACIÃ“N DE DATOS
# ============================================================

df = load_market_core()
lob_mapping_df = load_lob_mapping()
company_mapping_df = load_company_mapping()
formato_290_status = load_formato_290_status()

if df.empty:
    st.error(
        "Data not available. The demo database could not be loaded. "
        "Please confirm that data/database/insurance_market.duckdb exists."
    )
    st.stop()

CORE_REQUIRED_COLUMNS = [
    "country",
    "source",
    "period_date",
    "year",
    "month",
    "company_standard",
    "line_of_business_standard",
    "city",
    "metric_name",
    "metric_value",
    "source_file",
]

if not safe_has_columns(df, CORE_REQUIRED_COLUMNS):
    st.error(
        "Data not available. The demo database is missing required columns for the dashboard."
    )
    if DEBUG_MODE:
        missing_cols = sorted(set(CORE_REQUIRED_COLUMNS) - set(df.columns))
        st.write({"missing_columns": missing_cols})
    st.stop()

df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
df["year"] = df["year"].astype(int)
df["month"] = df["month"].astype(int)
df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
df = normalize_core_market_units(df)
company_aliases_df = load_company_aliases()
analysis_df = apply_line_labels(apply_company_aliases(df.copy(), company_aliases_df))
company_display_lookup = {}
if "company_display_name" in analysis_df.columns:
    company_display_lookup = (
        analysis_df[["company_standard", "company_display_name"]]
        .dropna()
        .drop_duplicates()
        .set_index("company_standard")["company_display_name"]
        .to_dict()
    )
line_display_lookup = {}
if "line_of_business_display_name" in analysis_df.columns:
    line_display_lookup = (
        analysis_df[["line_of_business_standard", "line_of_business_display_name"]]
        .dropna()
        .drop_duplicates()
        .set_index("line_of_business_standard")["line_of_business_display_name"]
        .to_dict()
    )

last_update = df["period_date"].max()
analysis_last_update = analysis_df["period_date"].max()
run_time = datetime.now()

# ============================================================
# HEADER
# ============================================================

render_top_header(
    APP_NAME,
    "Regional market intelligence platform for brokers and strategic decision-making. Colombia is the active data module for the current internal release.",
    kicker="Internal broker intelligence platform",
)

# ============================================================
# NAVIGATION AND FILTERS
# ============================================================

PAGE_OPTIONS = [
    "Market Overview",
    "Company Explorer",
    "Line of Business Explorer",
    "Company Brief",
    "AI Brief",
    "News / External Intelligence",
    "Technical Signals",
    "Reinsurance View",
    "Data Status",
    "Reports / Export",
    "Data Table",
]

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## Filters & Info")
st.sidebar.caption("Colombia Internal v1")
st.sidebar.markdown(f"**Build:** {BUILD_VERSION}")
st.sidebar.markdown(f"**DB mode:** {DB_MODE_LABEL}")

country_options = sorted(analysis_df["country"].dropna().unique())
if not country_options:
    warn_and_stop("Data not available for the selected source.")

is_formato_290_core = get_core_market_table_name() == "fact_market_core_formato_290"
render_section_header("Context Filters", "Select the workspace and market context for the analysis.")

if is_formato_290_core:
    (
        filter_col_module,
        filter_col_country,
        filter_col_year,
        filter_col_month,
        filter_col_mode,
    ) = st.columns([1.9, 1.1, 1.0, 1.2, 2.2])
    (
        filter_col_company,
        filter_col_line,
    ) = st.columns([1.8, 2.4])
else:
    (
        filter_col_module,
        filter_col_country,
        filter_col_years,
        filter_col_company,
        filter_col_line,
        filter_col_city,
    ) = st.columns([1.9, 1.1, 1.25, 1.7, 2.15, 1.3])

with filter_col_module:
    selected_view = st.selectbox(
        "Module",
        PAGE_OPTIONS,
        index=0,
        key="main_navigation",
    )

with filter_col_country:
    selected_country = st.selectbox(
        "Country",
        country_options,
        index=0,
        key="filter_country",
    )

country_df = analysis_df[analysis_df["country"] == selected_country]

years = sorted(country_df["year"].dropna().unique())
if not years:
    warn_and_stop("Data not available for the selected country.")

selected_reporting_year = None
selected_month_cutoff = None
comparison_mode = "Latest available cut"
comparison_context_label = "Latest available cut"

if is_formato_290_core:
    years = [int(year) for year in years]
    latest_period_for_country = country_df["period_date"].max()
    latest_year = int(latest_period_for_country.year)
    latest_month = int(latest_period_for_country.month)
    year_options = ["All years"] + years
    with filter_col_year:
        selected_reporting_year_option = st.selectbox(
            "Year",
            year_options,
            index=0,
            key="filter_reporting_year",
        )
    selected_reporting_year = None if selected_reporting_year_option == "All years" else int(selected_reporting_year_option)
    comparison_modes = [
        "YTD vs same period previous year",
        "Full year vs previous full year",
        "Selected month vs same month previous year",
    ]
    with filter_col_mode:
        comparison_mode = st.selectbox(
            "Comparison mode",
            comparison_modes,
            index=0,
            key="filter_comparison_mode",
        )
    if selected_reporting_year is None:
        selected_year_available_months = sorted(country_df["month"].dropna().astype(int).unique())
        selected_years_scope = years
        default_month = latest_month
    else:
        selected_year_available_months = sorted(
            country_df.loc[country_df["year"].astype(int) == selected_reporting_year, "month"]
            .dropna()
            .astype(int)
            .unique()
        )
        selected_years_scope = [selected_reporting_year]
        default_month = latest_month if selected_reporting_year == latest_year else min(12, max(selected_year_available_months))
    if comparison_mode == "Full year vs previous full year":
        default_month = 12
    with filter_col_month:
        selected_month_cutoff = st.selectbox(
            "Month cutoff",
            list(range(1, 13)),
            index=max(0, default_month - 1),
            format_func=lambda value: MONTH_NAME.get(value, str(value)),
            key="filter_month_cutoff",
        )
    if comparison_mode == "Full year vs previous full year" and selected_month_cutoff != 12:
        selected_month_cutoff = 12
    country_df = apply_formato_290_period_mode(
        country_df,
        selected_years_scope,
        selected_month_cutoff,
        comparison_mode,
    )
    if country_df.empty:
        render_empty_state(
            "No data available for the selected reporting period.",
            "Select another year, month cutoff or comparison mode."
        )
        st.stop()
    claims_mask = country_df["metric_name"].astype(str).eq("claims")
    country_df.loc[claims_mask, "metric_value"] = country_df.loc[claims_mask, "metric_value"].abs()
    selected_years = sorted(country_df["year"].dropna().astype(int).unique())
    if comparison_mode == "Full year vs previous full year":
        comparison_context_label = (
            "Full-year comparison through December, all complete years"
            if selected_reporting_year is None
            else f"Full-year {selected_reporting_year} through December"
        )
    elif comparison_mode == "Selected month vs same month previous year":
        comparison_context_label = (
            f"{MONTH_NAME.get(selected_month_cutoff, selected_month_cutoff)} monthly movement, all years"
            if selected_reporting_year is None
            else f"{MONTH_NAME.get(selected_month_cutoff, selected_month_cutoff)} {selected_reporting_year} monthly movement"
        )
    else:
        comparison_context_label = (
            f"YTD through {MONTH_NAME.get(selected_month_cutoff, selected_month_cutoff)}, all years"
            if selected_reporting_year is None
            else f"YTD through {MONTH_NAME.get(selected_month_cutoff, selected_month_cutoff)} {selected_reporting_year}"
        )
else:
    with filter_col_years:
        year_mode = st.selectbox(
            "Years",
            ["All years", "Latest year", "Custom years"],
            index=0,
            key="filter_year_mode",
        )

    if year_mode == "Latest year":
        selected_years = [max(years)]
    elif year_mode == "Custom years":
        selected_years = st.multiselect(
            "Custom years",
            years,
            default=years,
            help="Select one or more years for the current workspace.",
            key="filter_years",
        )
    else:
        selected_years = years
    comparison_context_label = "Latest available annual cut by year"

if not selected_years:
    render_empty_state(
        "Please select at least one year to continue.",
        "Use the Years filter above to restore the dashboard."
    )
    st.stop()

company_options = ["TODAS"] + sorted(country_df["company_standard"].dropna().unique())
with filter_col_company:
    selected_company = st.selectbox(
        "Company",
        company_options,
        format_func=lambda value: company_display_lookup.get(value, value),
        help="Select a company or keep TODAS for the full selected market.",
        key="filter_company",
    )

line_options = ["TODOS"] + sorted(country_df["line_of_business_standard"].dropna().unique())
with filter_col_line:
    selected_line = st.selectbox(
        "Line of business",
        line_options,
        format_func=lambda value: line_display_lookup.get(value, value),
        help="Select a line of business or keep TODOS for all lines.",
        key="filter_line",
    )

if is_formato_290_core:
    selected_city = "TODAS"
else:
    city_options = ["TODAS"] + sorted(country_df["city"].dropna().unique())
    with filter_col_city:
        selected_city = st.selectbox(
            "City",
            city_options,
            help="Use city only when local market detail is needed.",
            key="filter_city",
        )

st.sidebar.divider()

render_sidebar_label("Signal settings")

minimum_premium_mm = st.sidebar.number_input(
    "Minimum premium for technical signals (COP MM)",
    min_value=0,
    value=1000,
    step=100
)

minimum_premium = minimum_premium_mm * 1_000_000

st.sidebar.divider()

with st.sidebar.expander("About this tool", expanded=False):
    st.write("Internal broker intelligence platform for market, company, reinsurance and export workflows.")
    st.write("Current mode: Streamlit Cloud demo.")
    st.write("Data update mode: static snapshot / manual pipeline.")
    st.write("External news: curated/manual.")
    st.write("AI Brief: internal-data deterministic mode.")
    st.write(f"Database mode: {DB_MODE_LABEL}.")
    st.write(f"Database file in use: {DB_PATH.as_posix()}.")
    st.write("Modules: Market Intelligence, Broker Preparation, Reinsurance, Outputs and Governance.")
    st.markdown("**Build version:** Formato 290 broker analytics v2")
    st.write("Branch expected: demo-streamlit-cloud")
    st.write("Commit marker: 0344ed9")
    st.write("UI marker: month-cutoff-comparison-mode")

with st.sidebar.expander("Data context", expanded=False):
    st.write(f"Coverage: {selected_country}.")
    st.write(f"Core table: {get_core_market_table_name() or 'not available'}.")
    st.write("Target source: Datos Abiertos Colombia / SFC Formato 290, dataset e967-4a8r.")
    if is_formato_290_core:
        st.write(f"Comparison basis: {comparison_context_label}.")
    st.write(
        "Last update: "
        f"{analysis_last_update.strftime('%d/%m/%Y') if pd.notna(analysis_last_update) else 'N/A'}."
    )

with st.sidebar.expander("About data & methodology", expanded=False):
    st.write(
        "The migration target is SFC Formato 290 from Datos Abiertos Colombia. If the Formato 290 "
        "core table is not present yet, the app explicitly falls back to the prior Fasecolda snapshot "
        "until the regulatory ingestion is run and validated."
    )
    st.write(CLAIMS_PREMIUM_RATIO_NOTE)
    st.write(
        "Formato 290 period basis requires business confirmation before annualized growth "
        "or full-year comparisons are used."
    )

# ============================================================
# FILTRO PRINCIPAL
# ============================================================

filtered_df = country_df[country_df["year"].isin(selected_years)]

if selected_company != "TODAS":
    filtered_df = filtered_df[filtered_df["company_standard"] == selected_company]

if selected_line != "TODOS":
    filtered_df = filtered_df[filtered_df["line_of_business_standard"] == selected_line]

if selected_city != "TODAS":
    filtered_df = filtered_df[filtered_df["city"] == selected_city]

if filtered_df.empty:
    render_empty_state(
        "No data available for this selection.",
        "Try selecting a broader year range, all companies, or all lines of business."
    )
    st.stop()

premium_df = filtered_df[filtered_df["metric_name"] == "gross_written_premium"]
claims_df = filtered_df[filtered_df["metric_name"] == "claims"]
snapshot_year = int(filtered_df["year"].max()) if not filtered_df.empty else None
snapshot_df = filtered_df[filtered_df["year"] == snapshot_year].copy() if snapshot_year is not None else filtered_df.copy()
snapshot_label = (
    f"latest selected period {snapshot_year} ({comparison_context_label})"
    if snapshot_year is not None
    else comparison_context_label
)
technical_bridge_df = apply_line_labels(apply_company_aliases(load_formato_290_technical_bridge(), company_aliases_df))
if is_formato_290_core and not technical_bridge_df.empty:
    bridge_scope_df = prepare_bridge_scope(
        technical_bridge_df,
        selected_years_scope,
        selected_month_cutoff,
        company=selected_company,
        line=selected_line,
    )
    bridge_snapshot_df = (
        bridge_scope_df[bridge_scope_df["year"] == snapshot_year].copy()
        if snapshot_year is not None and "year" in bridge_scope_df.columns
        else bridge_scope_df.copy()
    )
else:
    bridge_scope_df = pd.DataFrame()
    bridge_snapshot_df = pd.DataFrame()

# ============================================================
# TAB 1 â€” MARKET OVERVIEW
# ============================================================

if selected_view == "Market Overview":
    try:
        render_section_header(
            "Market Summary",
            f"Executive snapshot for {comparison_context_label}.",
        )

        snapshot_premium_df = filter_real_lob_rows(snapshot_df[snapshot_df["metric_name"] == "gross_written_premium"].copy())
        snapshot_claims_df = filter_real_lob_rows(snapshot_df[snapshot_df["metric_name"] == "claims"].copy())
        chart_bridge_snapshot_df = filter_real_lob_rows(bridge_snapshot_df)
        chart_bridge_scope_df = filter_real_lob_rows(bridge_scope_df)
        display_filtered_df = filter_real_lob_rows(filtered_df)

        total_premium = snapshot_premium_df["metric_value"].sum()
        total_claims = snapshot_claims_df["metric_value"].sum()
        claims_ratio = safe_divide(total_claims, total_premium)
        active_companies = snapshot_premium_df.loc[snapshot_premium_df["metric_value"] != 0, "company_standard"].nunique()
        active_lines = snapshot_premium_df.loc[snapshot_premium_df["metric_value"] != 0, "line_of_business_standard"].nunique()
        company_premium_total = snapshot_premium_df.groupby("company_standard")["metric_value"].sum().sort_values(ascending=False)
        top5_concentration = safe_divide(company_premium_total.head(5).sum(), total_premium)

        summary_cols_1 = st.columns(5)
        with summary_cols_1[0]:
            render_metric_card("Written Premium", format_millions(total_premium), "Selected period")
        with summary_cols_1[1]:
            render_metric_card(CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(claims_ratio), "Uses absolute signed claims movement")
        with summary_cols_1[2]:
            render_metric_card("Active Companies", f"{active_companies:,}", "Non-zero written premium")
        with summary_cols_1[3]:
            render_metric_card("Active Lines", f"{active_lines:,}", "Non-zero written premium")
        with summary_cols_1[4]:
            render_metric_card("Top 5 Concentration", format_percentage(top5_concentration), "Top 5 companies / market")

        render_section_header("Market Share by Company", f"Primary company-level market view - {snapshot_label}.")
        market_share = (
            snapshot_premium_df
            .groupby(["company_standard", "company_display_name", "company_short_name"], as_index=False)["metric_value"]
            .sum()
            .sort_values("metric_value", ascending=False)
        )
        if not market_share.empty and market_share["metric_value"].sum() > 0:
            market_share["market_share"] = market_share["metric_value"] / market_share["metric_value"].sum()
            market_share_top = market_share.head(15).sort_values("market_share", ascending=True)
            fig_share = px.bar(
                market_share_top,
                y="company_short_name",
                x="market_share",
                orientation="h",
                title="Top 15 companies by market share",
                labels={"company_short_name": "Company", "market_share": "Market Share"},
                hover_data={"company_display_name": True, "metric_value": ":,.0f", "company_short_name": False},
            )
            fig_share.update_xaxes(tickformat=".1%")
            st.plotly_chart(fig_share, width="stretch")
        else:
            st.info("No written premium is available to calculate market share.")

        render_section_header("Line-of-Business Ranking", f"Top lines by written premium - {snapshot_label}.")
        premium_by_line = (
            snapshot_premium_df
            .groupby("line_of_business_standard", as_index=False)["metric_value"]
            .sum()
            .sort_values("metric_value", ascending=False)
            .head(15)
            .sort_values("metric_value", ascending=True)
        )
        if not premium_by_line.empty:
            premium_by_line["value_mm"] = premium_by_line["metric_value"] / 1_000_000
            fig_line = px.bar(
                premium_by_line,
                y="line_of_business_standard",
                x="value_mm",
                orientation="h",
                title="Top 15 lines of business by written premium",
                labels={"line_of_business_standard": "Line of business", "value_mm": "COP MM"},
            )
            st.plotly_chart(fig_line, width="stretch")
        else:
            st.info("No real line-of-business premium data is available for this selection.")

        if not chart_bridge_snapshot_df.empty:
            render_section_header("Reinsurance Snapshot", "Line-level ceded premium view from Formato 290.")
            bridge_by_line = summarize_bridge(chart_bridge_snapshot_df, ["ramo_name_clean"])
            bridge_by_line = bridge_by_line.sort_values("ceded_premium", ascending=False).head(15).sort_values("ceded_premium", ascending=True)
            if not bridge_by_line.empty:
                bridge_by_line["ceded_mm"] = bridge_by_line["ceded_premium"] / 1_000_000
                fig_ceded_line = px.bar(
                    bridge_by_line,
                    y="ramo_name_clean",
                    x="ceded_mm",
                    orientation="h",
                    title="Top lines by ceded premium",
                    labels={"ramo_name_clean": "Line of business", "ceded_mm": "COP MM"},
                    hover_data={"cession_ratio": ":.1%", "retention_ratio": ":.1%"},
                )
                st.plotly_chart(fig_ceded_line, width="stretch")
            st.caption("Cession and retention ratios are usable with warning until sign convention and denominator basis are approved.")

            render_section_header("Technical Profitability", "Line-level official Technical Result from Formato 290.")
            tech_by_line = summarize_bridge(chart_bridge_snapshot_df, ["ramo_name_clean"])
            tech_by_line = tech_by_line.sort_values("technical_result", ascending=False).head(15).sort_values("technical_result", ascending=True)
            if not tech_by_line.empty:
                tech_by_line["technical_result_mm"] = tech_by_line["technical_result"] / 1_000_000
                fig_tech_line = px.bar(
                    tech_by_line,
                    y="ramo_name_clean",
                    x="technical_result_mm",
                    orientation="h",
                    title="Top lines by Technical Result",
                    labels={"ramo_name_clean": "Line of business", "technical_result_mm": "COP MM"},
                    hover_data={"technical_result_ratio": ":.1%"},
                )
                st.plotly_chart(fig_tech_line, width="stretch")
            st.caption(
                "Technical Result comes from Formato 290 UC14 / Subcuenta 999. A negative value indicates a negative technical result on the selected technical reporting basis; it is not final company profit/loss. Technical Result Ratio denominator remains under business review."
            )

        render_section_header("Market Trends", "Evolution of market scale, claims movement, reinsurance and technical result.")
        year_summary = display_filtered_df.groupby(["year", "metric_name"], as_index=False)["metric_value"].sum()
        year_summary["value_mm"] = year_summary["metric_value"] / 1_000_000
        year_summary["metric_label"] = year_summary["metric_name"].map({"gross_written_premium": "Written Premium", "claims": "Incurred Claims"})
        fig_year = px.line(
            year_summary,
            x="year",
            y="value_mm",
            color="metric_label",
            markers=True,
            title=f"Written Premium and Incurred Claims evolution - {comparison_context_label}",
            labels={"year": "Year", "value_mm": "COP MM", "metric_label": "Metric"},
        )
        fix_year_axis(fig_year, year_summary["year"].unique())
        st.plotly_chart(fig_year, width="stretch")

        yearly_lr = prepare_premium_claims_summary(display_filtered_df, ["year"])
        yearly_lr["premium_growth"] = yearly_lr["primas"].pct_change()
        yearly_lr["primas_mm"] = yearly_lr["primas"] / 1_000_000
        yearly_lr["siniestros_mm"] = yearly_lr["siniestros"] / 1_000_000
        col_a, col_b = st.columns(2)
        with col_a:
            fig_lr = px.line(
                yearly_lr,
                x="year",
                y="siniestralidad",
                markers=True,
                title=f"{CLAIMS_PREMIUM_RATIO_LABEL_EN} by year",
                labels={"year": "Year", "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN},
            )
            fix_year_axis(fig_lr, yearly_lr["year"].unique())
            fig_lr.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_lr, width="stretch")
        with col_b:
            if not chart_bridge_scope_df.empty:
                bridge_by_year = summarize_bridge(chart_bridge_scope_df, ["year"])
                bridge_by_year["ceded_mm"] = bridge_by_year["ceded_premium"] / 1_000_000
                bridge_by_year["technical_result_mm"] = bridge_by_year["technical_result"] / 1_000_000
                bridge_trend = bridge_by_year.melt(
                    id_vars=["year"],
                    value_vars=["ceded_mm", "technical_result_mm"],
                    var_name="metric",
                    value_name="value_mm",
                )
                bridge_trend["metric"] = bridge_trend["metric"].map({"ceded_mm": "Ceded Premium", "technical_result_mm": "Technical Result"})
                fig_bridge_trend = px.line(
                    bridge_trend,
                    x="year",
                    y="value_mm",
                    color="metric",
                    markers=True,
                    title="Ceded Premium and Technical Result evolution",
                    labels={"year": "Year", "value_mm": "COP MM", "metric": "Metric"},
                )
                fix_year_axis(fig_bridge_trend, bridge_trend["year"].unique())
                st.plotly_chart(fig_bridge_trend, width="stretch")
            else:
                fig_growth = px.bar(
                    yearly_lr,
                    x="year",
                    y="premium_growth",
                    title="Written Premium Growth",
                    labels={"year": "Year", "premium_growth": "Growth"},
                )
                fix_year_axis(fig_growth, yearly_lr["year"].unique())
                fig_growth.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_growth, width="stretch")

        st.subheader("Annual Summary")
        yearly_display = make_display_summary(yearly_lr)
        render_dataframe(
            yearly_display[["year", "primas", "siniestros", CLAIMS_PREMIUM_RATIO_LABEL_ES, "premium_growth"]],
            width="stretch",
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 2 â€” COMPANY EXPLORER
# ============================================================

if selected_view == "Company Explorer":
    try:
        render_section_header(
            "Company Explorer",
            "Analyze company scale, portfolio mix, reinsurance profile and interim technical profitability.",
        )

        if selected_company == "TODAS":
            render_empty_state(
                "Select a company to open the Company Explorer.",
                "Use the Company filter above to view company-level trends and portfolio mix."
            )
        else:
            company_df = filtered_df[filtered_df["company_standard"] == selected_company]
            company_summary = prepare_premium_claims_summary(company_df, ["year"])
            company_summary["premium_growth"] = company_summary["primas"].pct_change()
            company_summary["primas_mm"] = company_summary["primas"] / 1_000_000
            company_summary["siniestros_mm"] = company_summary["siniestros"] / 1_000_000
            latest_company_year = int(company_summary["year"].max()) if not company_summary.empty else None

            company_bridge_scope = bridge_scope_df.copy()
            company_bridge_snapshot = bridge_snapshot_df.copy()
            if not company_bridge_scope.empty and selected_company != "TODAS":
                company_bridge_scope = company_bridge_scope[company_bridge_scope["company_name_clean"] == selected_company]
                company_bridge_snapshot = company_bridge_snapshot[company_bridge_snapshot["company_name_clean"] == selected_company]
            bridge_company_total = summarize_bridge(company_bridge_snapshot, []) if not company_bridge_snapshot.empty else pd.DataFrame()
            bridge_row = bridge_company_total.iloc[0] if not bridge_company_total.empty else {}

            if latest_company_year:
                latest_company_row = company_summary[company_summary["year"] == latest_company_year]
                latest_company_premium = latest_company_row["primas"].sum()
                latest_company_claims = latest_company_row["siniestros"].sum()
                latest_company_lr = safe_divide(latest_company_claims, latest_company_premium)

                kpi_cols = st.columns(6)
                with kpi_cols[0]:
                    render_metric_card("Written Premium", format_millions(latest_company_premium), f"{latest_company_year} selected line")
                with kpi_cols[1]:
                    render_metric_card(CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(latest_company_lr), "Selected company and line")
                with kpi_cols[2]:
                    render_metric_card("Ceded Premium", format_millions(bridge_row.get("ceded_premium") if bridge_row is not None else None), "Formato 290 bridge")
                with kpi_cols[3]:
                    render_metric_card("Cession Ratio", format_percentage(bridge_row.get("cession_ratio") if bridge_row is not None else None), "Usable with warning")
                with kpi_cols[4]:
                    render_metric_card("Technical Result", format_millions(bridge_row.get("technical_result") if bridge_row is not None else None), "UC14 / Subcuenta 999")
                with kpi_cols[5]:
                    render_metric_card("Technical Result Ratio", format_percentage(bridge_row.get("technical_result_ratio") if bridge_row is not None else None), "Denominator under review")

            render_section_header(
                "Company Portfolio Mix — all lines of business",
                f"Largest company lines by written premium for {snapshot_label}.",
            )
            if selected_line != "TODOS":
                st.info(
                    "This portfolio mix intentionally ignores the selected line-of-business filter "
                    "to show the company's full business distribution. KPI cards and trend charts respect the selected line."
                )

            portfolio_company_df = country_df[country_df["company_standard"] == selected_company].copy()
            if snapshot_year is not None:
                portfolio_company_df = portfolio_company_df[portfolio_company_df["year"] == snapshot_year].copy()
            portfolio_company_df = filter_real_lob_rows(portfolio_company_df)
            company_premium = portfolio_company_df[portfolio_company_df["metric_name"] == "gross_written_premium"]
            company_by_line = (
                company_premium
                .groupby("line_of_business_standard", as_index=False)["metric_value"]
                .sum()
                .rename(columns={"metric_value": "written_premium"})
                .sort_values("written_premium", ascending=False)
                .head(15)
            )
            total_company_portfolio = company_premium["metric_value"].sum()
            company_by_line["portfolio_share"] = company_by_line["written_premium"].apply(lambda value: safe_divide(value, total_company_portfolio))
            company_line_lr = prepare_premium_claims_summary(portfolio_company_df, ["line_of_business_standard"])
            company_by_line = company_by_line.merge(
                company_line_lr[["line_of_business_standard", "siniestralidad"]],
                on="line_of_business_standard",
                how="left",
            )
            company_portfolio_bridge = prepare_bridge_scope(
                technical_bridge_df,
                selected_years_scope,
                selected_month_cutoff,
                company=selected_company,
                line="TODOS",
            ) if is_formato_290_core and not technical_bridge_df.empty else pd.DataFrame()
            if snapshot_year is not None and not company_portfolio_bridge.empty:
                company_portfolio_bridge = company_portfolio_bridge[company_portfolio_bridge["year"] == snapshot_year]
            company_portfolio_bridge = filter_real_lob_rows(company_portfolio_bridge)
            bridge_by_line = summarize_bridge(company_portfolio_bridge, ["ramo_name_clean"]) if not company_portfolio_bridge.empty else pd.DataFrame()
            if not bridge_by_line.empty:
                company_by_line = company_by_line.merge(
                    bridge_by_line[["ramo_name_clean", "ceded_premium", "retained_premium", "cession_ratio", "retention_ratio", "technical_result", "technical_result_ratio"]],
                    left_on="line_of_business_standard",
                    right_on="ramo_name_clean",
                    how="left",
                ).drop(columns=["ramo_name_clean"], errors="ignore")
            company_by_line["written_premium_mm"] = company_by_line["written_premium"] / 1_000_000
            portfolio_table = company_by_line.copy()
            for money_col in ["written_premium", "ceded_premium", "retained_premium", "technical_result"]:
                if money_col in portfolio_table.columns:
                    portfolio_table[money_col] = portfolio_table[money_col].map(format_millions)
            for ratio_col in ["portfolio_share", "siniestralidad", "cession_ratio", "retention_ratio", "technical_result_ratio"]:
                if ratio_col in portfolio_table.columns:
                    portfolio_table[ratio_col] = portfolio_table[ratio_col].map(format_percentage)
            render_dataframe(portfolio_table, width="stretch")

            fig_company_line = px.bar(
                company_by_line.sort_values("written_premium", ascending=True),
                y="line_of_business_standard",
                x="written_premium_mm",
                orientation="h",
                title=f"Company portfolio mix by written premium - {snapshot_label}",
                labels={"line_of_business_standard": "Line of business", "written_premium_mm": "COP MM"},
            )
            st.plotly_chart(fig_company_line, width="stretch")

            if not company_portfolio_bridge.empty:
                render_section_header("Reinsurance Profile", "Ceded and retained premium by line for the selected company.")
                re_profile = summarize_bridge(company_portfolio_bridge, ["ramo_name_clean"])
                re_profile = re_profile.sort_values("ceded_premium", ascending=False).head(15)
                re_profile["ceded_mm"] = re_profile["ceded_premium"] / 1_000_000
                re_profile["retained_mm"] = re_profile["retained_premium"] / 1_000_000
                re_left, re_right = st.columns(2)
                with re_left:
                    fig_re_line = px.bar(
                        re_profile.sort_values("ceded_premium", ascending=True),
                        y="ramo_name_clean",
                        x="ceded_mm",
                        orientation="h",
                        title="Ceded Premium by line",
                        labels={"ramo_name_clean": "Line of business", "ceded_mm": "COP MM"},
                        hover_data={"cession_ratio": ":.1%", "retention_ratio": ":.1%"},
                    )
                    st.plotly_chart(fig_re_line, width="stretch")
                with re_right:
                    fig_ret_line = px.bar(
                        re_profile.sort_values("retained_premium", ascending=True),
                        y="ramo_name_clean",
                        x="retained_mm",
                        orientation="h",
                        title="Retained Premium by line",
                        labels={"ramo_name_clean": "Line of business", "retained_mm": "COP MM"},
                        hover_data={"cession_ratio": ":.1%", "retention_ratio": ":.1%"},
                    )
                    st.plotly_chart(fig_ret_line, width="stretch")

                render_section_header("Technical Profitability", "Technical Result by line, shown as an interim profitability indicator.")
                tech_profile = re_profile.sort_values("technical_result", ascending=False).head(15).copy()
                tech_profile["technical_result_mm"] = tech_profile["technical_result"] / 1_000_000
                fig_tech_line = px.bar(
                    tech_profile.sort_values("technical_result", ascending=True),
                    y="ramo_name_clean",
                    x="technical_result_mm",
                    orientation="h",
                    title="Technical Result by line",
                    labels={"ramo_name_clean": "Line of business", "technical_result_mm": "COP MM"},
                    hover_data={"technical_result_ratio": ":.1%"},
                )
                st.plotly_chart(fig_tech_line, width="stretch")
                st.caption("Technical Result Ratio is useful as an interim profitability indicator, but its denominator still requires business approval.")

            render_section_header("Written Premium and Incurred Claims Evolution", f"Selected company and line - {comparison_context_label}.")
            col_a, col_b = st.columns(2)
            with col_a:
                fig_company_premium = px.line(
                    company_summary,
                    x="year",
                    y="primas_mm",
                    markers=True,
                    title="Written Premium evolution - selected company and line",
                    labels={"year": "Year", "primas_mm": "COP MM"},
                )
                fix_year_axis(fig_company_premium, company_summary["year"].unique())
                st.plotly_chart(fig_company_premium, width="stretch")
            with col_b:
                fig_company_lr = px.line(
                    company_summary,
                    x="year",
                    y="siniestralidad",
                    markers=True,
                    title=f"{CLAIMS_PREMIUM_RATIO_LABEL_EN} evolution - selected company and line",
                    labels={"year": "Year", "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN},
                )
                fix_year_axis(fig_company_lr, company_summary["year"].unique())
                fig_company_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_company_lr, width="stretch")

            render_section_header("Annual Company Summary", f"Written premium, incurred claims and technical ratio - {comparison_context_label}.")
            company_display = make_display_summary(company_summary)
            render_dataframe(
                company_display[["year", "primas", "siniestros", CLAIMS_PREMIUM_RATIO_LABEL_ES, "premium_growth"]],
                width="stretch",
            )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 3 â€” LINE OF BUSINESS EXPLORER
# ============================================================

if selected_view == "Line of Business Explorer":
    try:
        render_section_header(
            "Line of Business Explorer",
            "Treaty-oriented benchmark for a selected line, with company position, peers, reinsurance and technical result context.",
        )

        if selected_line == "TODOS":
            render_empty_state(
                "Select a line of business to open the Line of Business Explorer.",
                "Use the Line of business filter above or keep Market Overview for all lines."
            )
        else:
            line_market_df = filter_real_lob_rows(country_df[country_df["line_of_business_standard"] == selected_line].copy())
            line_df = filter_real_lob_rows(filtered_df[filtered_df["line_of_business_standard"] == selected_line].copy())
            line_market_snapshot_df = line_market_df[line_market_df["year"] == snapshot_year].copy() if snapshot_year is not None else line_market_df.copy()
            selected_line_snapshot_df = line_df[line_df["year"] == snapshot_year].copy() if snapshot_year is not None else line_df.copy()

            if line_market_df.empty or line_market_snapshot_df.empty:
                render_empty_state(
                    "No line-of-business data is available for this selection.",
                    "Try another line, period mode or broader filter context."
                )
            else:
                market_line_premium_df = line_market_snapshot_df[line_market_snapshot_df["metric_name"] == "gross_written_premium"]
                market_line_claims_df = line_market_snapshot_df[line_market_snapshot_df["metric_name"] == "claims"]
                selected_premium_df = selected_line_snapshot_df[selected_line_snapshot_df["metric_name"] == "gross_written_premium"]
                selected_claims_df = selected_line_snapshot_df[selected_line_snapshot_df["metric_name"] == "claims"]

                total_line_premium = market_line_premium_df["metric_value"].sum()
                total_line_claims = market_line_claims_df["metric_value"].sum()
                line_claims_ratio = safe_divide(total_line_claims, total_line_premium)
                selected_written_premium = selected_premium_df["metric_value"].sum()
                selected_claims = selected_claims_df["metric_value"].sum()
                selected_claims_ratio = safe_divide(selected_claims, selected_written_premium)

                peer_summary = prepare_premium_claims_summary(line_market_snapshot_df, ["company_standard"])
                company_meta = (
                    line_market_snapshot_df[["company_standard", "company_display_name", "company_short_name"]]
                    .drop_duplicates()
                )
                peer_summary = peer_summary.merge(company_meta, on="company_standard", how="left")
                peer_summary = peer_summary.sort_values("primas", ascending=False).reset_index(drop=True)
                peer_summary["rank"] = peer_summary.index + 1
                peer_summary["market_share"] = peer_summary["primas"].apply(lambda value: safe_divide(value, total_line_premium))
                peer_summary["selected_company"] = peer_summary["company_standard"].eq(selected_company)
                line_active_companies = peer_summary.loc[peer_summary["primas"] != 0, "company_standard"].nunique()
                line_top5_concentration = safe_divide(peer_summary["primas"].head(5).sum(), total_line_premium)

                line_market_bridge_scope = prepare_bridge_scope(
                    technical_bridge_df,
                    selected_years_scope,
                    selected_month_cutoff,
                    company="TODAS",
                    line=selected_line,
                ) if is_formato_290_core and not technical_bridge_df.empty else pd.DataFrame()
                line_market_bridge_scope = filter_real_lob_rows(line_market_bridge_scope)
                line_market_bridge_snapshot = (
                    line_market_bridge_scope[line_market_bridge_scope["year"] == snapshot_year].copy()
                    if snapshot_year is not None and not line_market_bridge_scope.empty
                    else line_market_bridge_scope.copy()
                )
                bridge_by_company = summarize_bridge(
                    line_market_bridge_snapshot,
                    ["company_name_clean", "company_display_name", "company_short_name"],
                ) if not line_market_bridge_snapshot.empty else pd.DataFrame()
                if not bridge_by_company.empty:
                    peer_summary = peer_summary.merge(
                        bridge_by_company[
                            [
                                "company_name_clean",
                                "ceded_premium",
                                "retained_premium",
                                "cession_ratio",
                                "retention_ratio",
                                "technical_result",
                                "technical_result_ratio",
                            ]
                        ],
                        left_on="company_standard",
                        right_on="company_name_clean",
                        how="left",
                    ).drop(columns=["company_name_clean"], errors="ignore")

                selected_peer = peer_summary[peer_summary["company_standard"] == selected_company]
                if selected_company == "TODAS" or selected_peer.empty:
                    selected_rank = None
                    selected_market_share = None if selected_company != "TODAS" else 1.0
                    selected_ceded = selected_retained = selected_cession = selected_technical = selected_technical_ratio = None
                    selected_context_name = "Selected line market"
                else:
                    selected_row = selected_peer.iloc[0]
                    selected_rank = int(selected_row.get("rank")) if pd.notna(selected_row.get("rank")) else None
                    selected_market_share = selected_row.get("market_share")
                    selected_ceded = selected_row.get("ceded_premium")
                    selected_retained = selected_row.get("retained_premium")
                    selected_cession = selected_row.get("cession_ratio")
                    selected_technical = selected_row.get("technical_result")
                    selected_technical_ratio = selected_row.get("technical_result_ratio")
                    selected_context_name = selected_row.get("company_short_name") or selected_company

                if selected_company == "TODAS":
                    line_bridge_total = summarize_bridge(line_market_bridge_snapshot, []) if not line_market_bridge_snapshot.empty else pd.DataFrame()
                    line_bridge_row = line_bridge_total.iloc[0] if not line_bridge_total.empty else {}
                    selected_written_premium = total_line_premium
                    selected_claims_ratio = line_claims_ratio
                    selected_ceded = line_bridge_row.get("ceded_premium") if line_bridge_row is not None else None
                    selected_retained = line_bridge_row.get("retained_premium") if line_bridge_row is not None else None
                    selected_cession = line_bridge_row.get("cession_ratio") if line_bridge_row is not None else None
                    selected_technical = line_bridge_row.get("technical_result") if line_bridge_row is not None else None
                    selected_technical_ratio = line_bridge_row.get("technical_result_ratio") if line_bridge_row is not None else None

                render_section_header("Selected Line Snapshot", f"{selected_context_name} in {selected_line} - {snapshot_label}.")
                kpi_row_1 = st.columns(4)
                with kpi_row_1[0]:
                    render_metric_card("Written Premium", format_millions(selected_written_premium), "Selected company and line" if selected_company != "TODAS" else "Selected line market")
                with kpi_row_1[1]:
                    render_metric_card("Market Share in Selected Line", format_percentage(selected_market_share), "Company share within the line" if selected_company != "TODAS" else "Full line market")
                with kpi_row_1[2]:
                    rank_text = f"#{selected_rank}" if selected_rank else "N/A"
                    render_metric_card("Ranking Position", rank_text, "By written premium in selected line")
                with kpi_row_1[3]:
                    render_metric_card(CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(selected_claims_ratio), "Uses absolute signed claims movement")
                kpi_row_2 = st.columns(4)
                with kpi_row_2[0]:
                    render_metric_card("Ceded Premium", format_millions(selected_ceded), "Usable with warning")
                with kpi_row_2[1]:
                    render_metric_card("Cession Ratio", format_percentage(selected_cession), "Basis under review")
                with kpi_row_2[2]:
                    render_metric_card("Retained Premium", format_millions(selected_retained), "Usable with warning")
                with kpi_row_2[3]:
                    render_metric_card("Technical Result", format_millions(selected_technical), "UC14 / Subcuenta 999")

                with st.expander("Technical Result note", expanded=False):
                    st.write(
                        "Technical Result comes from Formato 290 UC14 / Subcuenta 999. A negative value reflects the technical account result reported for the selected company, line and period. It is not automatically equivalent to final company profit/loss."
                    )
                    if selected_line == "TERREMOTO" and selected_technical is not None and pd.notna(selected_technical) and selected_technical < 0:
                        st.write(
                            "Negative results in catastrophe lines may reflect technical accounting movements, expenses, reinsurance, reserves or limited premium volume, not necessarily a recent catastrophic event."
                        )

                if selected_company != "TODAS":
                    render_section_header("Company vs Market Benchmark", "How the selected company compares with the selected line market.")
                    benchmark_cols = st.columns(5)
                    with benchmark_cols[0]:
                        render_metric_card("Company Premium", format_millions(selected_written_premium), "Selected company")
                    with benchmark_cols[1]:
                        render_metric_card("Line Market Premium", format_millions(total_line_premium), "All companies")
                    with benchmark_cols[2]:
                        render_metric_card("Company Claims Ratio", format_percentage(selected_claims_ratio), "Selected company")
                    with benchmark_cols[3]:
                        render_metric_card("Line Average Claims Ratio", format_percentage(line_claims_ratio), "All companies")
                    with benchmark_cols[4]:
                        render_metric_card("Technical Result Ratio", format_percentage(selected_technical_ratio), "Denominator under review")

                render_section_header("Peer Comparison Table", "Companies writing the selected line, ranked by written premium.")
                peer_display = peer_summary.copy()
                peer_display["selected"] = peer_display["selected_company"].map(lambda value: "Selected" if value else "")
                for money_col in ["primas", "siniestros", "ceded_premium", "retained_premium", "technical_result"]:
                    if money_col in peer_display.columns:
                        peer_display[money_col] = peer_display[money_col].map(format_millions)
                for ratio_col in ["market_share", "siniestralidad", "cession_ratio", "retention_ratio", "technical_result_ratio"]:
                    if ratio_col in peer_display.columns:
                        peer_display[ratio_col] = peer_display[ratio_col].map(format_percentage)
                peer_cols = [
                    "rank",
                    "selected",
                    "company_short_name",
                    "company_display_name",
                    "primas",
                    "market_share",
                    "siniestralidad",
                    "ceded_premium",
                    "cession_ratio",
                    "retained_premium",
                    "technical_result",
                    "technical_result_ratio",
                ]
                render_dataframe(peer_display[[col for col in peer_cols if col in peer_display.columns]].head(25), width="stretch")

                render_section_header("Evolution of Selected Company in Selected Line", f"Trends for {selected_context_name} - {comparison_context_label}.")
                selected_evolution_df = line_df.copy() if selected_company != "TODAS" else line_market_df.copy()
                selected_summary = prepare_premium_claims_summary(selected_evolution_df, ["year"])
                selected_summary["primas_mm"] = selected_summary["primas"] / 1_000_000
                line_market_summary = prepare_premium_claims_summary(line_market_df, ["year"])
                market_share_evolution = selected_summary[["year", "primas", "siniestralidad"]].merge(
                    line_market_summary[["year", "primas"]].rename(columns={"primas": "market_primas"}),
                    on="year",
                    how="left",
                )
                market_share_evolution["market_share"] = market_share_evolution.apply(lambda row: safe_divide(row["primas"], row["market_primas"]), axis=1)

                evo_cols = st.columns(2)
                with evo_cols[0]:
                    fig_line_premium = px.line(
                        selected_summary,
                        x="year",
                        y="primas_mm",
                        markers=True,
                        title="Written Premium evolution",
                        labels={"year": "Year", "primas_mm": "COP MM"},
                    )
                    fix_year_axis(fig_line_premium, selected_summary["year"].unique())
                    st.plotly_chart(fig_line_premium, width="stretch")
                with evo_cols[1]:
                    fig_market_share = px.line(
                        market_share_evolution,
                        x="year",
                        y="market_share",
                        markers=True,
                        title="Market Share evolution in selected line",
                        labels={"year": "Year", "market_share": "Market Share"},
                    )
                    fix_year_axis(fig_market_share, market_share_evolution["year"].unique())
                    fig_market_share.update_yaxes(tickformat=".1%")
                    st.plotly_chart(fig_market_share, width="stretch")

                evo_cols_2 = st.columns(2)
                with evo_cols_2[0]:
                    fig_claims_ratio = px.line(
                        selected_summary,
                        x="year",
                        y="siniestralidad",
                        markers=True,
                        title=f"{CLAIMS_PREMIUM_RATIO_LABEL_EN} evolution",
                        labels={"year": "Year", "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN},
                    )
                    fix_year_axis(fig_claims_ratio, selected_summary["year"].unique())
                    fig_claims_ratio.update_yaxes(tickformat=".1%")
                    st.plotly_chart(fig_claims_ratio, width="stretch")
                with evo_cols_2[1]:
                    selected_bridge_scope = prepare_bridge_scope(
                        technical_bridge_df,
                        selected_years_scope,
                        selected_month_cutoff,
                        company=selected_company,
                        line=selected_line,
                    ) if is_formato_290_core and not technical_bridge_df.empty else pd.DataFrame()
                    if selected_company == "TODAS":
                        selected_bridge_scope = line_market_bridge_scope.copy()
                    selected_bridge_scope = filter_real_lob_rows(selected_bridge_scope)
                    if not selected_bridge_scope.empty:
                        bridge_year = summarize_bridge(selected_bridge_scope, ["year"])
                        bridge_year["technical_result_mm"] = bridge_year["technical_result"] / 1_000_000
                        fig_tech_evo = px.line(
                            bridge_year,
                            x="year",
                            y="technical_result_mm",
                            markers=True,
                            title="Technical Result evolution",
                            labels={"year": "Year", "technical_result_mm": "COP MM"},
                        )
                        fix_year_axis(fig_tech_evo, bridge_year["year"].unique())
                        st.plotly_chart(fig_tech_evo, width="stretch")
                    else:
                        st.info("Technical Result evolution is not available for this selection.")

                if not selected_bridge_scope.empty:
                    bridge_year = summarize_bridge(selected_bridge_scope, ["year"])
                    bridge_year["ceded_mm"] = bridge_year["ceded_premium"] / 1_000_000
                    re_evo = bridge_year.melt(
                        id_vars=["year"],
                        value_vars=["ceded_mm", "cession_ratio"],
                        var_name="metric",
                        value_name="value",
                    )
                    re_evo["metric"] = re_evo["metric"].map({"ceded_mm": "Ceded Premium (COP MM)", "cession_ratio": "Cession Ratio"})
                    fig_re_evo = px.line(
                        re_evo,
                        x="year",
                        y="value",
                        color="metric",
                        markers=True,
                        title="Ceded Premium and Cession Ratio evolution",
                        labels={"year": "Year", "value": "Value", "metric": "Metric"},
                    )
                    fix_year_axis(fig_re_evo, re_evo["year"].unique())
                    st.plotly_chart(fig_re_evo, width="stretch")

                render_section_header("Line Market Structure", "Compact market structure context for the selected line.")
                structure_cols = st.columns([1, 2])
                with structure_cols[0]:
                    render_metric_card("Top 5 Concentration", format_percentage(line_top5_concentration), "Within selected line")
                    render_metric_card("Active Companies", f"{line_active_companies:,}", "Non-zero written premium")
                with structure_cols[1]:
                    top10 = peer_summary.head(10).sort_values("primas", ascending=True).copy()
                    top10["primas_mm"] = top10["primas"] / 1_000_000
                    fig_top10 = px.bar(
                        top10,
                        y="company_short_name",
                        x="primas_mm",
                        orientation="h",
                        title="Top 10 companies by written premium in selected line",
                        labels={"company_short_name": "Company", "primas_mm": "COP MM"},
                        hover_data={"company_display_name": True, "market_share": ":.1%"},
                    )
                    st.plotly_chart(fig_top10, width="stretch")
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 4 â€” COMPANY BRIEF
# ============================================================

if selected_view == "Company Brief":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "Executive Broker Briefing",
            "Structured meeting preparation generated from the selected filters and public structured market data.",
        )

        if selected_company == "TODAS":
            render_empty_state(
                "Select a company to generate the Company Brief.",
                "The brief is designed for company-level broker preparation. Use Market Overview when Company is TODAS."
            )
        else:
            company_df = filtered_df[filtered_df["company_standard"] == selected_company]

            market_reference_df = country_df[country_df["year"].isin(selected_years)]

            if selected_line != "TODOS":
                market_reference_df = market_reference_df[
                    market_reference_df["line_of_business_standard"] == selected_line
                ]

            if selected_city != "TODAS":
                market_reference_df = market_reference_df[
                    market_reference_df["city"] == selected_city
                ]

            mapped_company_for_re = map_company_using_mapping_table(
                selected_company,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country
            )
            mapped_line_for_re = None
            if selected_line != "TODOS":
                mapped_line_for_re = map_lob_using_mapping_table(
                    selected_line,
                    target_source="FASECOLDA - INDICADORES DE GESTION",
                    country=selected_country
                )

            try:
                company_reinsurance_wide = build_reinsurance_wide(
                    indicadores_df,
                    selected_country,
                    company=mapped_company_for_re,
                    line=mapped_line_for_re,
                )
                company_reinsurance_summary = summarize_reinsurance(company_reinsurance_wide)

                brief = build_company_brief(
                    country=selected_country,
                    company=selected_company,
                    selected_line=selected_line,
                    selected_years=selected_years,
                    company_df=company_df,
                    market_df=market_reference_df,
                    reinsurance_summary=company_reinsurance_summary,
                    minimum_premium=minimum_premium,
                    reinsurance_wide=company_reinsurance_wide,
                )
            except Exception as exc:
                render_section_error(exc)
                st.stop()

            market_position = brief.get("market_position", {})
            company_summary = prepare_premium_claims_summary(company_df, ["year"])

            render_section_header("Quick Indicators")
            if not company_summary.empty:
                latest_year = int(company_summary["year"].max())
                latest_row = company_summary[company_summary["year"] == latest_year]
                latest_premium = latest_row["primas"].sum()
                latest_claims = latest_row["siniestros"].sum()
                latest_lr = latest_claims / latest_premium if latest_premium else None
                latest_growth = latest_row["premium_growth"].iloc[0] if "premium_growth" in latest_row else pd.NA
                rank_value = (
                    f"#{int(market_position['rank'])}"
                    if pd.notna(market_position.get("rank", pd.NA))
                    else "N/A"
                )

                quick_cards = [
                    ("Year", str(latest_year)),
                    ("Premiums", format_millions(latest_premium)),
                    ("Claims", format_millions(latest_claims)),
                    (CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(latest_lr)),
                    ("Market share", format_percentage(market_position.get("market_share", pd.NA))),
                    ("Market position", rank_value),
                ]
                for start in range(0, len(quick_cards), 3):
                    quick_cols = st.columns(3)
                    for col, (label, value) in zip(quick_cols, quick_cards[start:start + 3]):
                        with col:
                            render_metric_card(label, value)
                if pd.notna(latest_growth):
                    st.caption(f"Premium growth: {format_percentage(latest_growth)} in the latest available year.")
            else:
                st.info("Not enough data available for quick indicators.")

            render_section_header("Executive Narrative")
            st.write(brief["executive_summary"])

            render_section_header(
                "Executive Snapshot",
                "Interpretive signals for portfolio focus, growth, broker angle and reinsurance discussion.",
            )
            snapshot_items = brief.get("executive_snapshot", [])
            duplicate_snapshot_labels = {
                "selected year",
                "premium",
                "Incurred Claims / Written Premium",
                "market position",
                "market share",
                "recent growth",
            }
            snapshot_items = [
                item for item in snapshot_items
                if str(item.get("label", "")).strip().lower() not in duplicate_snapshot_labels
            ]
            if snapshot_items:
                for start in range(0, len(snapshot_items), 3):
                    snapshot_cols = st.columns(3)
                    for col, item in zip(snapshot_cols, snapshot_items[start:start + 3]):
                        with col:
                            render_metric_card(
                                item.get("label", "Metric"),
                                item.get("value", "N/A"),
                                item.get("detail", "Not enough data available for this metric."),
                            )
            else:
                st.info("Not enough data available for the executive snapshot.")

            with st.container():
                render_section_header("Market Position", "Ranking and benchmark view for the selected market context.")

                top_companies = market_position.get("top_companies", pd.DataFrame())
                if isinstance(top_companies, pd.DataFrame) and not top_companies.empty:
                    top_companies_chart = top_companies.copy()
                    top_companies_chart["premium_mm"] = top_companies_chart["primas"] / 1_000_000
                    top_companies_chart["premium_display"] = top_companies_chart["primas"].map(format_millions)
                    if "market_share" in top_companies_chart.columns:
                        top_companies_chart["market_share_display"] = top_companies_chart["market_share"].map(format_percentage)
                    else:
                        total_top_premium = top_companies_chart["primas"].sum()
                        top_companies_chart["market_share_display"] = top_companies_chart["primas"].map(
                            lambda value: format_percentage(safe_divide(value, total_top_premium))
                        )
                    top_companies_chart["rank"] = range(1, len(top_companies_chart) + 1)
                    top_companies_chart["company_label"] = top_companies_chart["company_standard"].map(
                        lambda value: f"{value} (selected)" if value == selected_company else value
                    )
                    render_dataframe(
                        top_companies_chart[
                            ["rank", "company_label", "premium_display", "market_share_display"]
                        ],
                        width="stretch",
                        hide_index=True,
                    )
                    fig_top_market = px.bar(
                        top_companies_chart,
                        x="company_label",
                        y="premium_mm",
                        title=f"Top 5 companies by premium - {market_position.get('latest_year', 'selected year')}",
                        labels={
                            "company_label": "Company",
                            "premium_mm": "Premiums in COP MM",
                        },
                    )
                    st.plotly_chart(fig_top_market, width="stretch")

                render_section_header("Main Competitors", "Companies with the largest premium in the same selected market context.")
                competitors_display = brief.get("competitors", pd.DataFrame()).copy()
                if competitors_display.empty:
                    st.info("Not enough data available to calculate competitors.")
                else:
                    competitors_display["premium"] = competitors_display["primas"].map(format_millions)
                    competitors_display["market_share_display"] = competitors_display["market_share"].map(format_percentage)
                    competitors_display["claims_premiums_display"] = competitors_display["siniestralidad"].map(format_percentage)
                    competitors_display["difference_vs_selected"] = competitors_display["premium_difference_vs_selected"].map(format_millions)
                    competitors_display["company_label"] = competitors_display.apply(
                        lambda row: f"{row['company_standard']} (selected)" if row["is_selected_company"] else row["company_standard"],
                        axis=1,
                    )
                    render_dataframe(
                        competitors_display[
                            [
                                "company_label",
                                "premium",
                                "market_share_display",
                                "claims_premiums_display",
                                "difference_vs_selected",
                            ]
                        ],
                        width="stretch",
                    )

                render_section_header("Technical Performance", "Premium, claims and incurred-claims-to-written-premium ratio evolution.")
                premium_evolution = brief["premium_evolution"].copy()
                if not premium_evolution.empty:
                    premium_evolution["primas_display"] = premium_evolution["primas"].map(format_millions)
                    premium_evolution["siniestros_display"] = premium_evolution["siniestros"].map(format_millions)
                    premium_evolution["siniestralidad_display"] = premium_evolution["siniestralidad"].map(format_percentage)
                    premium_evolution["premium_growth_display"] = premium_evolution["premium_growth"].map(format_percentage)
                    premium_evolution_display = premium_evolution.rename(
                        columns={"siniestralidad_display": CLAIMS_PREMIUM_RATIO_LABEL_ES}
                    )
                    render_dataframe(
                        premium_evolution_display[
                            [
                                "year",
                                "primas_display",
                                "siniestros_display",
                                CLAIMS_PREMIUM_RATIO_LABEL_ES,
                                "premium_growth_display",
                            ]
                        ],
                        width="stretch"
                    )

                render_section_header("Market Share Evolution", "Company premium relative to the selected market reference by year.")
                market_share_display = brief["market_share"].copy()
                if not market_share_display.empty:
                    market_share_display["company_premium"] = market_share_display["primas"].map(format_millions)
                    market_share_display["market_premium"] = market_share_display["market_primas"].map(format_millions)
                    market_share_display["market_share_display"] = market_share_display["market_share"].map(format_percentage)
                    render_dataframe(
                        market_share_display[
                            ["year", "company_premium", "market_premium", "market_share_display"]
                        ],
                        width="stretch"
                    )

                render_section_header("Portfolio Mix", "Top lines, portfolio share, Incurred Claims / Written Premium and growth.")
                st.caption(brief.get("portfolio_interpretation", "Not enough data available for portfolio interpretation."))
                portfolio_display = brief.get("portfolio_mix", pd.DataFrame()).copy()
                if portfolio_display.empty:
                    st.info("Data not available")
                else:
                    portfolio_display["premium_display"] = portfolio_display["primas"].map(format_millions)
                    portfolio_display["portfolio_share_display"] = portfolio_display["portfolio_share"].map(format_percentage)
                    portfolio_display["claims_premiums_display"] = portfolio_display["siniestralidad"].map(format_percentage)
                    portfolio_display["premium_growth_display"] = portfolio_display["premium_growth"].map(format_percentage)
                    render_dataframe(
                        portfolio_display[
                            [
                                "line_of_business_standard",
                                "premium_display",
                                "portfolio_share_display",
                                "claims_premiums_display",
                                "premium_growth_display",
                            ]
                        ],
                        width="stretch"
                    )
                    evolution_chart = premium_evolution.copy()
                    evolution_chart["primas_mm"] = evolution_chart["primas"] / 1_000_000
                    evolution_chart["siniestros_mm"] = evolution_chart["siniestros"] / 1_000_000
                    evolution_value_chart = evolution_chart.melt(
                        id_vars=["year"],
                        value_vars=["primas_mm", "siniestros_mm"],
                        var_name="metric",
                        value_name="value_mm",
                    )
                    evolution_value_chart["metric"] = evolution_value_chart["metric"].map(
                        {"primas_mm": "Premiums", "siniestros_mm": "Claims"}
                    )
                    chart_col_1, chart_col_2 = st.columns(2)
                    with chart_col_1:
                        fig_values = px.line(
                            evolution_value_chart,
                            x="year",
                            y="value_mm",
                            color="metric",
                            markers=True,
                            title="Premium and claims evolution",
                            labels={"year": "Year", "value_mm": "COP MM", "metric": "Metric"},
                        )
                        fix_year_axis(fig_values, evolution_chart["year"].unique())
                        st.plotly_chart(fig_values, width="stretch")
                    with chart_col_2:
                        fig_ratio = px.line(
                            evolution_chart,
                            x="year",
                            y="siniestralidad",
                            markers=True,
                            title="Incurred Claims / Written Premium evolution",
                            labels={"year": "Year", "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN},
                        )
                        fix_year_axis(fig_ratio, evolution_chart["year"].unique())
                        fig_ratio.update_yaxes(tickformat=".1%")
                        st.plotly_chart(fig_ratio, width="stretch")
                    if str(selected_line).strip().upper() not in {"TODOS", "ALL", "ALL LINES"}:
                        st.info("Portfolio mix is not shown because a single line of business is selected.")
                    else:
                        portfolio_chart = portfolio_display.copy()
                        portfolio_chart["premium_mm"] = portfolio_chart["primas"] / 1_000_000
                        fig_portfolio_mix = px.bar(
                            portfolio_chart,
                            x="line_of_business_standard",
                            y="premium_mm",
                            title="Portfolio mix by premium",
                            labels={
                                "line_of_business_standard": "Line of business",
                                "premium_mm": "Premiums in COP MM",
                            },
                        )
                        st.plotly_chart(fig_portfolio_mix, width="stretch")

                render_section_header("Growth Signals", "Lines with material growth or changing Incurred Claims / Written Premium.")
                growth_display = brief.get("growth_signals", pd.DataFrame()).copy()
                if growth_display.empty:
                    st.info("Data not available")
                else:
                    growth_display["primas_display"] = growth_display["primas"].map(format_millions)
                    growth_display["premium_growth_display"] = growth_display["premium_growth"].map(format_percentage)
                    growth_display["claims_premiums_change_display"] = growth_display["claims_premiums_change"].map(format_percentage)
                    render_dataframe(
                        growth_display[
                            [
                                "line_of_business_standard",
                                "year",
                                "primas_display",
                                "premium_growth_display",
                                "claims_premiums_change_display",
                                "growth_signal",
                            ]
                        ],
                        width="stretch"
                    )

                render_section_header("Incurred Claims / Written Premium Watch", "Lines with deteriorating analytical incurred-claims-to-written-premium ratio.")
                deterioration_display = brief["deteriorating_loss_ratio_lines"].copy()
                if deterioration_display.empty:
                    st.info("Data not available")
                else:
                    deterioration_display["siniestralidad_display"] = deterioration_display["siniestralidad"].map(format_percentage)
                    deterioration_display["loss_ratio_change_display"] = deterioration_display["loss_ratio_change"].map(format_percentage)
                    deterioration_display = deterioration_display.rename(
                        columns={
                            "siniestralidad_display": CLAIMS_PREMIUM_RATIO_LABEL_ES,
                            "loss_ratio_change_display": "Change in Incurred Claims / Written Premium",
                        }
                    )
                    render_dataframe(
                        deterioration_display[
                            [
                                "line_of_business_standard",
                                "year",
                                CLAIMS_PREMIUM_RATIO_LABEL_ES,
                                "Change in Incurred Claims / Written Premium",
                            ]
                        ],
                        width="stretch"
                    )

                render_section_header("Reinsurance Signals", "Compact preview from exploratory Indicadores de Gestion where available.")
                reinsurance_signals = brief.get("reinsurance_signals", {})
                st.write(brief["reinsurance_text"])
                re_line_signals = (
                    reinsurance_signals.get("line_signals", pd.DataFrame())
                    if isinstance(reinsurance_signals, dict)
                    else pd.DataFrame()
                )
                if isinstance(re_line_signals, pd.DataFrame) and not re_line_signals.empty:
                    re_line_display = re_line_signals.copy()
                    re_line_display["ceded_premium"] = re_line_display["reinsurance_ceded_premium"].map(format_millions)
                    re_line_display["retained_premium"] = re_line_display["retained_premium"].map(format_millions)
                    re_line_display["cession_ratio_display"] = re_line_display["cession_ratio"].map(format_percentage)
                    re_line_display["retention_ratio_display"] = re_line_display["retention_ratio"].map(format_percentage)
                    with st.expander("Line-level reinsurance preview", expanded=False):
                        render_dataframe(
                            re_line_display[
                                [
                                    "line_of_business_standard",
                                    "ceded_premium",
                                    "retained_premium",
                                    "cession_ratio_display",
                                    "retention_ratio_display",
                                ]
                            ],
                            width="stretch",
                        )

                render_section_header("Technical Alerts", "Broker-useful signals, not definitive underwriting conclusions.")
                alerts = brief.get("alerts", [])
                if not alerts:
                    st.info("No technical alerts available for the selected filters.")
                else:
                    for alert in alerts:
                        if isinstance(alert, dict):
                            st.write(
                                f"**{alert.get('severity', 'Review')} - {alert.get('title', 'Alert')}**: "
                                f"{alert.get('explanation', '')}"
                            )
                            st.caption(f"Suggested follow-up: {alert.get('follow_up', 'Review with the client.')}")
                        else:
                            st.write(f"- {alert}")

                render_section_header("Broker Questions")
                for question in brief["questions"]:
                    st.write(f"- {question}")

            st.divider()

            st.markdown("### Company One-Pager")

            one_pager_markdown = render_one_pager_markdown(
                brief,
                company=selected_company,
                country=selected_country,
            )
            one_pager_html = render_markdown_as_html(
                one_pager_markdown,
                title=f"{selected_company} one-pager",
            )

            chart_col_a, chart_col_b = st.columns(2)

            with chart_col_a:
                if not brief["premium_evolution"].empty:
                    chart_data = brief["premium_evolution"].copy()
                    chart_data["primas_mm"] = chart_data["primas"] / 1_000_000
                    fig_one_pager_premium = px.line(
                        chart_data,
                        x="year",
                        y="primas_mm",
                        markers=True,
                        title="Premium evolution",
                        labels={"year": "Year", "primas_mm": "Premiums in COP MM"},
                    )
                    fix_year_axis(fig_one_pager_premium, chart_data["year"].unique())
                    st.plotly_chart(fig_one_pager_premium, width="stretch")

            with chart_col_b:
                if not brief["main_lines"].empty:
                    chart_lines = brief["main_lines"].copy()
                    chart_lines["premium_mm"] = chart_lines["gross_written_premium"] / 1_000_000
                    fig_one_pager_lines = px.bar(
                        chart_lines,
                        x="line_of_business_standard",
                        y="premium_mm",
                        title="Top lines of business",
                        labels={
                            "line_of_business_standard": "Line",
                            "premium_mm": "Premiums in COP MM",
                        },
                    )
                    st.plotly_chart(fig_one_pager_lines, width="stretch")

            with st.expander("Preview one-pager markdown", expanded=False):
                st.code(one_pager_markdown, language="markdown")

            col_export_a, col_export_b, col_export_c = st.columns(3)

            with col_export_a:
                st.download_button(
                    label="Download company brief markdown",
                    data=brief["markdown"],
                    file_name=f"{selected_company.lower().replace(' ', '_')}_company_brief.md",
                    mime="text/markdown",
                    key="company_brief_tab_download_brief_md",
                )

            with col_export_b:
                st.download_button(
                    label="Download one-pager markdown",
                    data=one_pager_markdown,
                    file_name=f"{selected_company.lower().replace(' ', '_')}_one_pager.md",
                    mime="text/markdown",
                    key="company_brief_tab_download_one_pager_md",
                )

            with col_export_c:
                st.download_button(
                    label="Download one-pager HTML",
                    data=one_pager_html,
                    file_name=f"{selected_company.lower().replace(' ', '_')}_one_pager.html",
                    mime="text/html",
                    key="company_brief_tab_download_one_pager_html",
                )

            st.warning(
                "Methodology note: this brief is generated from structured public market data. "
                "Incurred Claims / Written Premium is an analytical incurred-claims-to-written-premium ratio, not necessarily Fasecolda's "
                "official technical loss ratio or combined ratio. Indicadores de Gestion 2025 remains "
                "exploratory and figures should be validated before formal client or market use."
            )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 5 â€” AI BRIEF
# ============================================================

if selected_view == "AI Brief":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "AI Brief",
            "Deterministic broker intelligence brief generated from internal structured data.",
        )

        st.info(
            "This version uses structured internal data and rule-based generation. "
            "External AI, web intelligence, company news and key-people search are not connected yet."
        )

        ai_config = get_ai_config()
        if ai_config.configured:
            st.caption(
                f"External AI provider detected ({ai_config.status_message}), but Phase 4C does not call external AI APIs."
            )
        else:
            st.caption("No AI API key is required for this internal-data brief.")

        ai_company_options = sorted(country_df["company_standard"].dropna().unique())
        if selected_company != "TODAS" and selected_company in ai_company_options:
            ai_company_index = ai_company_options.index(selected_company)
        else:
            ai_company_index = 0

        ai_line_options = ["TODOS"] + sorted(country_df["line_of_business_standard"].dropna().unique())
        ai_line_index = ai_line_options.index(selected_line) if selected_line in ai_line_options else 0

        ai_col_a, ai_col_b = st.columns(2)

        with ai_col_a:
            brief_type = st.selectbox(
                "Brief type",
                [
                    "Pre-meeting company brief",
                    "Reinsurance discussion brief",
                    "Portfolio review brief",
                    "Market comparison brief",
                    "Internal strategy brief",
                ],
                key="ai_brief_type",
            )
            ai_company = st.selectbox(
                "Company for AI brief",
                ai_company_options,
                index=ai_company_index,
                key="ai_company_select",
            )
            ai_line = st.selectbox(
                "Optional line of business",
                ai_line_options,
                index=ai_line_index,
                key="ai_line_select",
            )

        with ai_col_b:
            ai_years = st.multiselect(
                "Years for AI brief",
                years,
                default=selected_years,
                key="ai_years_select",
            )
            if not ai_years:
                st.warning("Select at least one year for the AI context. Using the latest available year for now.")
                ai_years = [max(years)]
            meeting_purpose = st.text_input(
                "Meeting purpose",
                value="Client meeting preparation",
                key="ai_meeting_purpose",
            )
            internal_question = st.text_area(
                "Focused internal-data question",
                value="What should I ask about reinsurance?",
                key="ai_internal_question",
                height=90,
            )

        ai_mapped_company = map_company_using_mapping_table(
            ai_company,
            target_source="FASECOLDA - INDICADORES DE GESTION",
            country=selected_country,
        )

        ai_mapped_line = None
        if ai_line != "TODOS":
            ai_mapped_line = map_lob_using_mapping_table(
                ai_line,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country,
            )

        try:
            ai_context = build_ai_brief_context(
                market_df=country_df,
                selected_country=selected_country,
                selected_company=ai_company,
                selected_lob=ai_line,
                selected_years=ai_years,
                meeting_purpose=meeting_purpose,
                brief_type=brief_type,
                indicadores_df=indicadores_df,
                mapped_company=ai_mapped_company,
                mapped_line=ai_mapped_line,
                minimum_premium=minimum_premium,
                data_status={
                    "database_mode": "Candidate local test" if USE_CANDIDATE_DB else "Stable demo",
                    "data_update_mode": "Static demo snapshot plus manual pipeline metadata",
                    "automatic_updates": "Manual-run pipeline available; scheduling not yet enabled",
                },
            )
            deterministic_brief = generate_ai_brief_from_context(ai_context)
        except Exception as exc:
            render_section_error(exc)
            st.stop()

        summary_col_a, summary_col_b, summary_col_c, summary_col_d = st.columns(4)
        company_context = ai_context.get("company_context", {})
        market_context = ai_context.get("market_context", {})
        reinsurance_context = ai_context.get("reinsurance_context", {})

        with summary_col_a:
            render_metric_card("Brief scope", ai_company, "Selected company")
        with summary_col_b:
            render_metric_card("Latest year", str(company_context.get("latest_year") or market_context.get("latest_year") or "N/A"))
        with summary_col_c:
            render_metric_card(
                "Premium",
                format_millions(company_context.get("premium") if ai_company != "TODAS" else market_context.get("premium")),
                "Selected scope",
            )
        with summary_col_d:
            render_metric_card(
                "Reinsurance",
                "Available" if reinsurance_context.get("available") else "Not available",
                "Indicadores de Gestion 2025",
            )

        render_section_header(
            "Internal-Data Answer",
            "Constrained response to the focused broker question using only app data.",
        )

        st.markdown(answer_ai_brief_question(internal_question, ai_context))

        render_section_header(
            "Broker-Ready AI Brief",
            "Copy-ready markdown generated from Company Brief, Reinsurance View and market context.",
        )

        st.markdown(deterministic_brief)

        with st.expander("Copy-ready brief", expanded=False):
            st.code(deterministic_brief, language="markdown")

        with st.expander("Structured internal context", expanded=False):
            st.code(context_to_json(ai_context), language="json")

        render_section_header(
            "External Intelligence Not Yet Connected",
            "These items are planned for later phases and are not used in this brief.",
        )

        st.write(
            "- Key people / leadership: planned for a later external-intelligence phase.\n"
            "- Company news: planned for the News module phase.\n"
            "- Ratings / financial statements: future enhancement after source and compliance review.\n"
            "- Live AI generation: future enhancement subject to secure API configuration."
        )

        st.warning(
            "Guardrails: this brief uses internal structured app data only. It does not include external "
            "news, ratings, financial statements, leadership/key people or live web search. Incurred Claims / Written Premium "
            "is analytical, not necessarily official technical siniestralidad or combined ratio. Reinsurance "
            "indicators remain exploratory where source limitations apply."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 6 â€” NEWS
# ============================================================

if selected_view == "News / External Intelligence":
    try:
        render_section_header(
            "Company News & External Intelligence",
            "Curated external context for treaty-broker meeting preparation. No live search is run in this phase.",
        )

        st.info(
            "Current mode: curated/manual external intelligence. The app reads a small committed template file "
            "and does not scrape, search the web, call news APIs, or require secrets."
        )

        curated_news_df = load_curated_company_news()
        key_people_df = load_key_people_template()

        news_company_options = ["TODAS"] + sorted(country_df["company_standard"].dropna().unique())
        news_company_index = (
            news_company_options.index(selected_company)
            if selected_company in news_company_options
            else 0
        )

        news_col_a, news_col_b = st.columns(2)
        with news_col_a:
            news_company = st.selectbox(
                "Company news focus",
                news_company_options,
                index=news_company_index,
                key="news_company_select",
            )
        with news_col_b:
            st.write("**Selected context**")
            st.caption(f"Country: {selected_country}")
            st.caption(f"Line of business: {'All lines' if selected_line == 'TODOS' else selected_line}")
            st.caption(f"Years: {', '.join(str(int(year)) for year in selected_years)}")

        company_news_context = build_company_news_context(
            curated_news_df,
            selected_company=news_company,
            selected_country=selected_country,
            selected_line=selected_line,
            selected_years=selected_years,
        )

        card_a, card_b, card_c, card_d = st.columns(4)
        with card_a:
            render_metric_card("Curated items", f"{company_news_context['total_items']:,}", "Manual file")
        with card_b:
            render_metric_card("Most recent date", company_news_context["latest_news_date"], "Curated item date")
        with card_c:
            render_metric_card("Top category", company_news_context["top_relevance_category"], "Broker relevance")
        with card_d:
            render_metric_card("Verified items", f"{company_news_context['verified_items']:,}", "Manual verification flag")

        render_section_header(
            "Curated Company News",
            "Source-based items manually curated for broker context.",
        )

        news_items_df = company_news_context["news_items"]
        if news_items_df.empty:
            render_empty_state(
                "No curated news available for the selected company yet.",
                "Add verified public items to data/external/company_news_curated.csv when external intelligence is ready."
            )
            st.write("External news ingestion is planned as a future enhancement.")
        else:
            for idx, (_, item) in enumerate(news_items_df.head(10).iterrows(), start=1):
                link = str(item.get("url") or "").strip()
                title = item.get("title", "Untitled news item")
                source = item.get("source", "Source not available")
                date_text = item.get("date_display", "Date not available")
                category = item.get("relevance_category", "Other")
                verification = item.get("verification_status", "Manual/unverified")
                with st.container():
                    if link:
                        st.markdown(f"#### {idx}. [{title}]({link})")
                    else:
                        st.markdown(f"#### {idx}. {title}")
                    st.write(f"Source: {source} | Date: {date_text} | Category: {category} | Status: {verification}")
                    st.write(item.get("summary", "Summary not available."))
                    st.info(f"Broker relevance: {item.get('broker_relevance', 'Review relevance before use.')}")
                    if item.get("notes"):
                        st.caption(f"Notes: {item.get('notes')}")

            st.download_button(
                label="Download curated company news CSV",
                data=news_items_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{news_company.lower().replace(' ', '_')}_news.csv",
                mime="text/csv",
                key="download_company_news_csv",
            )

        render_section_header(
            "Broker Interpretation",
            "Rule-based interpretation of curated external context.",
        )
        st.write(company_news_context["broker_relevance_summary"])

        render_section_header(
            "Suggested Broker Questions",
            "Questions generated from curated news categories and source context.",
        )
        for question in company_news_context["suggested_questions"]:
            st.write(f"- {question}")

        with st.expander("Company news context for future AI Brief integration", expanded=False):
            context_preview = {
                key: value
                for key, value in company_news_context.items()
                if key != "news_items"
            }
            context_preview["news_items"] = (
                news_items_df.drop(columns=["date"], errors="ignore")
                .head(10)
                .to_dict(orient="records")
                if not news_items_df.empty
                else []
            )
            st.json(context_preview)

        render_section_header(
            "Key People / Leadership Intelligence",
            "Manual-only placeholder. No web search and no invented people.",
        )

        if key_people_df.empty:
            st.info(
                "Key people search is not yet connected. This will be added in a future external intelligence phase."
            )
        else:
            people_df = key_people_df.copy()
            if news_company != "TODAS" and "company_name" in people_df.columns:
                people_df = people_df[
                    people_df["company_name"].astype(str).str.upper().str.contains(str(news_company).upper(), na=False)
                ]
            if people_df.empty:
                render_empty_state(
                    "No manually curated leadership data is available for the selected company.",
                    "Leadership intelligence remains manual-only and should not be inferred or invented."
                )
            else:
                render_dataframe(people_df, width="stretch", hide_index=True)

        with st.expander("Future live news mode", expanded=False):
            if ENABLE_LIVE_NEWS:
                st.warning(
                    "Live mode flag is enabled, but live retrieval is intentionally not implemented in Phase 4D."
                )
            else:
                st.write(
                    "Live news mode is disabled by default. A future provider-based implementation may use "
                    "approved APIs only, with caching and governance controls. No uncontrolled scraping will be used."
                )

        st.warning(
            "External intelligence is not the same as Fasecolda structured market data. News items should be "
            "treated as contextual information, with source/date/link validation required before formal use."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 7 â€” TECHNICAL SIGNALS
# ============================================================

if selected_view == "Technical Signals":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "Technical Signals",
            "Monitor growth, Incurred Claims / Written Premium pressure, market share movement and reinsurance cession signals.",
        )

        latest_year = max(selected_years) if selected_years else country_df["year"].max()

        try:
            technical_signals_df = build_technical_signals(
                market_df=filtered_df,
                indicadores_df=indicadores_df,
                country=selected_country,
                latest_year=latest_year,
                minimum_premium=minimum_premium,
            )
        except Exception as exc:
            render_section_error(exc)
            st.stop()

        st.markdown("### Broker-relevant signal table")

        if technical_signals_df.empty:
            render_empty_state(
                "No technical signals are available for this selection.",
                "Try a broader year range, all lines of business, or a lower minimum premium threshold."
            )
        else:
            signal_display = technical_signals_df.copy()
            signal_display["metric_display"] = signal_display.apply(
                lambda row: format_percentage(row["metric_value"])
                if any(
                    token in row["signal_type"].lower()
                    for token in ["growth", "ratio", "share"]
                )
                else format_millions(row["metric_value"]),
                axis=1,
            )
            render_dataframe(
                signal_display[
                    [
                        "signal_type",
                        "metric_display",
                        "year",
                        "company",
                        "line_of_business",
                        "explanation",
                        "source",
                    ]
                ],
                width="stretch",
            )

            watchlist_display = signal_display[signal_display["signal_type"] == "Broker watchlist"]
            if not watchlist_display.empty:
                st.markdown("### Broker watchlist")
                render_dataframe(
                    watchlist_display[
                        [
                            "metric_display",
                            "year",
                            "company",
                            "line_of_business",
                            "explanation",
                            "source",
                        ]
                    ].head(20),
                    width="stretch",
                )

            signals_csv = technical_signals_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="Download technical signals CSV",
                data=signals_csv,
                file_name="technical_signals.csv",
                mime="text/csv",
                key="technical_signals_download_csv",
            )

        render_section_header("Highest Premium Growth Companies", "Companies with the strongest latest-year premium growth above the selected threshold.")

        company_year = prepare_premium_claims_summary(filtered_df, ["company_standard", "year"])
        company_year = company_year.sort_values(["company_standard", "year"])
        company_year["premium_growth"] = company_year.groupby("company_standard")["primas"].pct_change()

        company_latest_growth = (
            company_year[
                (company_year["year"] == latest_year) &
                (company_year["primas"] >= minimum_premium)
            ]
            .dropna(subset=["premium_growth"])
            .sort_values("premium_growth", ascending=False)
            .head(15)
        )

        if not company_latest_growth.empty:
            fig_top_growth = px.bar(
                company_latest_growth,
                x="company_standard",
                y="premium_growth",
                title=f"Top premium growth by company - {latest_year}",
                labels={
                    "company_standard": "Company",
                    "premium_growth": "Growth"
                }
            )

            fig_top_growth.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_top_growth, width="stretch")
        else:
            render_empty_state(
                "No premium growth signals meet the selected threshold.",
                "Lower the minimum premium threshold or broaden the selected filters."
            )

        col_a, col_b = st.columns(2)

        with col_a:
            render_section_header(f"Highest Company {CLAIMS_PREMIUM_RATIO_LABEL_EN}", "Companies with the highest analytical incurred-claims-to-written-premium ratio above the selected threshold.")

            company_lr = prepare_premium_claims_summary(filtered_df, ["company_standard"])
            company_lr = company_lr[company_lr["primas"] >= minimum_premium]
            company_lr = company_lr.sort_values("siniestralidad", ascending=False).head(15)
            company_lr["primas_mm"] = company_lr["primas"] / 1_000_000

            if not company_lr.empty:
                fig_company_high_lr = px.bar(
                    company_lr,
                    x="company_standard",
                    y="siniestralidad",
                    title=f"Top companies by {CLAIMS_PREMIUM_RATIO_LABEL_EN}",
                    labels={
                        "company_standard": "Company",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN
                    },
                    hover_data=["primas_mm"]
                )

                fig_company_high_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_company_high_lr, width="stretch")
            else:
                render_empty_state(
                    "No companies meet the selected minimum premium threshold.",
                    "Lower the threshold or broaden the selected filters."
                )

        with col_b:
            render_section_header(f"Highest Line {CLAIMS_PREMIUM_RATIO_LABEL_EN}", "Lines of business with the highest analytical incurred-claims-to-written-premium ratio above the selected threshold.")

            line_lr = prepare_premium_claims_summary(filtered_df, ["line_of_business_standard"])
            line_lr = line_lr[line_lr["primas"] >= minimum_premium]
            line_lr = line_lr.sort_values("siniestralidad", ascending=False).head(15)
            line_lr["primas_mm"] = line_lr["primas"] / 1_000_000

            if not line_lr.empty:
                fig_line_high_lr = px.bar(
                    line_lr,
                    x="line_of_business_standard",
                    y="siniestralidad",
                    title=f"Top lines by {CLAIMS_PREMIUM_RATIO_LABEL_EN}",
                    labels={
                        "line_of_business_standard": "Line of business",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN
                    },
                    hover_data=["primas_mm"]
                )

                fig_line_high_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_line_high_lr, width="stretch")
            else:
                render_empty_state(
                    "No lines meet the selected minimum premium threshold.",
                    "Lower the threshold or broaden the selected filters."
                )

        render_section_header("Highest Premium Growth Lines", "Lines of business with the strongest latest-year premium growth above the selected threshold.")

        line_year = prepare_premium_claims_summary(filtered_df, ["line_of_business_standard", "year"])
        line_year = line_year.sort_values(["line_of_business_standard", "year"])
        line_year["premium_growth"] = line_year.groupby("line_of_business_standard")["primas"].pct_change()

        line_latest_growth = (
            line_year[
                (line_year["year"] == latest_year) &
                (line_year["primas"] >= minimum_premium)
            ]
            .dropna(subset=["premium_growth"])
            .sort_values("premium_growth", ascending=False)
            .head(15)
        )

        if not line_latest_growth.empty:
            fig_line_growth = px.bar(
                line_latest_growth,
                x="line_of_business_standard",
                y="premium_growth",
                title=f"Top premium growth by line - {latest_year}",
                labels={
                    "line_of_business_standard": "Line of business",
                    "premium_growth": "Growth"
                }
            )

            fig_line_growth.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_line_growth, width="stretch")
        else:
            render_empty_state(
                "No line growth signals meet the selected threshold.",
                "Lower the threshold or broaden the selected filters."
            )

        st.warning(
            "Nota: estas señales son automáticas y deben interpretarse considerando tamaño de cartera, "
            "cambios de clasificación, efectos extraordinarios y calidad de la información fuente."
        )
    except Exception as exc:
        render_section_error(exc)


# ============================================================
# TAB 6 â€” REINSURANCE VIEW
# ============================================================

if selected_view == "Reinsurance View":
    try:
        indicadores_df = load_indicadores_gestion_2025()
        indicadores_validation_df = load_indicadores_gestion_validation()
        indicadores_validation_flags_df = load_indicadores_gestion_validation_flags()
        pipeline_status = load_pipeline_status()
        readiness_df = load_metric_readiness_matrix()
        combined_readiness_df = load_combined_ratio_readiness()
        bridge_summary_df = load_technical_bridge_summary()
        formato_290_status = load_formato_290_status()

        render_section_header(
            "Reinsurance View",
            "Analyze cession, retention and treaty-broker discussion angles using exploratory reinsurance indicators.",
        )
        st.info(
            "Metodología: fuente Fasecolda - Indicadores de Gestión 2025. "
            "Estado: fuente complementaria exploratoria. "
            "Los ratios se recalculan a nivel agregado y no se suman. "
            "Los ramos agregados pueden duplicar ramos individuales y pueden excluirse de rankings. "
            "La fuente requiere revisión metodológica adicional antes de integrarse al modelo regional core."
        )

        if indicadores_df.empty:
            render_empty_state(
                "Reinsurance indicators are not available in the demo database.",
                "The module requires fact_indicadores_gestion_2025 before cession and retention views can be shown."
            )
        else:
            exclude_aggregate_lines = st.checkbox(
                "Exclude aggregate lines from rankings",
                value=True,
                help=(
                    "Excluye ramos con lob_group = AGGREGATE en el mapping formal "
                    "y totales como TOTAL DAÃ‘OS, TOTAL PERSONAS y TOTAL SEGURIDAD SOCIAL."
                )
            )

            indicadores_df["period_date"] = pd.to_datetime(indicadores_df["period_date"], errors="coerce")
            indicadores_df["year"] = pd.to_numeric(indicadores_df["year"], errors="coerce").astype("Int64")
            indicadores_df["metric_value"] = pd.to_numeric(indicadores_df["metric_value"], errors="coerce")

            re_df = indicadores_df[indicadores_df["country"] == selected_country].copy()
            re_df = re_df[re_df["year"].isin(selected_years)].copy()

            # Normalizar textos para comparar mejor entre fuentes
            re_df["company_standard_norm"] = re_df["company_standard"].astype(str).str.strip().str.upper()
            re_df["line_of_business_standard_norm"] = re_df["line_of_business_standard"].astype(str).str.strip().str.upper()
            aggregate_lob_lookup = get_aggregate_lob_lookup(
                country=selected_country,
                target_source="FASECOLDA - INDICADORES DE GESTION"
            )
            re_df["is_aggregate_lob"] = re_df["line_of_business_standard"].map(
                lambda value: normalize_match_text(value) in aggregate_lob_lookup
            )

            # Filtros alineados con la barra lateral
            if selected_company != "TODAS":
                mapped_company = map_company_using_mapping_table(
                    selected_company,
                    target_source="FASECOLDA - INDICADORES DE GESTION",
                    country=selected_country
                )

                if mapped_company is None:
                    st.warning(
                        f"La compañía seleccionada '{selected_company}' no tiene mapeo disponible "
                        "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                        "hasta que agreguemos esta equivalencia al mapping de compañías."
                    )
                    re_df = re_df.iloc[0:0]
                else:
                    mapped_company_norm = str(mapped_company).strip().upper()
                    re_df = re_df[re_df["company_standard_norm"] == mapped_company_norm]

                    if re_df.empty:
                        st.warning(
                            f"La compañía seleccionada '{selected_company}' fue mapeada como "
                            f"'{mapped_company}', pero no se encontraron registros en Indicadores de Gestión 2025."
                        )
                    else:
                        st.info(
                            f"Compañía mapeada para Indicadores de Gestión: "
                            f"'{selected_company}' â†’ '{mapped_company}'."
                        )

            if selected_line != "TODOS":
                mapped_line = map_lob_using_mapping_table(
                    selected_line,
                    target_source="FASECOLDA - INDICADORES DE GESTION",
                    country=selected_country
                )

                if mapped_line is None:
                    st.warning(
                        f"El ramo seleccionado '{selected_line}' no tiene mapeo disponible "
                        "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                        "hasta que agreguemos esta equivalencia al diccionario de ramos."
                    )
                    re_df = re_df.iloc[0:0]
                else:
                    mapped_line_norm = str(mapped_line).strip().upper()
                    re_df = re_df[re_df["line_of_business_standard_norm"] == mapped_line_norm]

                    if re_df.empty:
                        st.warning(
                            f"El ramo seleccionado '{selected_line}' fue mapeado como '{mapped_line}', "
                            "pero no se encontraron registros en Indicadores de Gestión 2025."
                        )
                    else:
                        st.info(
                            f"Ramo mapeado para Indicadores de Gestión: '{selected_line}' â†’ '{mapped_line}'."
                        )

            aggregate_metric_rows = int(re_df["is_aggregate_lob"].sum()) if not re_df.empty else 0
            aggregate_lines_available = sorted(
                re_df.loc[re_df["is_aggregate_lob"], "line_of_business_standard"]
                .dropna()
                .astype(str)
                .unique()
            )

            if exclude_aggregate_lines and aggregate_metric_rows:
                re_df = re_df[~re_df["is_aggregate_lob"]].copy()
                st.info(
                    f"Se excluyeron {aggregate_metric_rows:,} registros fuente de ramos agregados "
                    f"para reducir riesgo de duplicidad en rankings y KPIs exploratorios: "
                    f"{', '.join(aggregate_lines_available)}."
                )
            elif aggregate_metric_rows:
                st.warning(
                    "La vista incluye ramos agregados. Estos totales pueden duplicar ramos individuales "
                    "en rankings y KPIs exploratorios."
                )

            # Indicadores de Gestión no trae ciudad; por eso no aplicamos filtro de ciudad
            if selected_city != "TODAS":
                st.info(
                    "Nota: Indicadores de Gestión no contiene detalle por ciudad. "
                    "La Reinsurance View no aplica el filtro de ciudad."
                )

            if re_df.empty:
                render_empty_state(
                    "Reinsurance indicators are not available for this selection.",
                    "Try all companies, all lines of business, or a broader year range."
                )
                st.stop()

            # Pasar a formato ancho para calcular KPIs correctamente
            group_cols_re = [
                "country",
                "year",
                "company_standard",
                "line_of_business_standard"
            ]

            re_wide = (
                re_df.pivot_table(
                    index=group_cols_re,
                    columns="metric_name",
                    values="metric_value",
                    aggfunc="sum"
                )
                .reset_index()
            )

            re_wide.columns.name = None

            expected_cols = [
                "gross_written_premium",
                "retained_premium",
                "reinsurance_ceded_premium",
                "paid_claims",
                "retention_ratio",
                "reinsurance_cession_ratio"
            ]

            for col in expected_cols:
                if col not in re_wide.columns:
                    re_wide[col] = pd.NA

            market_re_df = indicadores_df[indicadores_df["country"] == selected_country].copy()
            market_re_df = market_re_df[market_re_df["year"].isin(selected_years)].copy()
            market_re_df["company_standard_norm"] = market_re_df["company_standard"].astype(str).str.strip().str.upper()
            market_re_df["line_of_business_standard_norm"] = market_re_df["line_of_business_standard"].astype(str).str.strip().str.upper()
            market_re_df["is_aggregate_lob"] = market_re_df["line_of_business_standard"].map(
                lambda value: normalize_match_text(value) in aggregate_lob_lookup
            )

            if selected_line != "TODOS":
                mapped_market_line = map_lob_using_mapping_table(
                    selected_line,
                    target_source="FASECOLDA - INDICADORES DE GESTION",
                    country=selected_country
                )
                if mapped_market_line is None:
                    market_re_df = market_re_df.iloc[0:0]
                else:
                    market_re_df = market_re_df[
                        market_re_df["line_of_business_standard_norm"] == str(mapped_market_line).strip().upper()
                    ]

            if exclude_aggregate_lines and not market_re_df.empty:
                market_re_df = market_re_df[~market_re_df["is_aggregate_lob"]].copy()

            if market_re_df.empty:
                market_re_wide = pd.DataFrame()
            else:
                market_re_wide = (
                    market_re_df.pivot_table(
                        index=group_cols_re,
                        columns="metric_name",
                        values="metric_value",
                        aggfunc="sum"
                    )
                    .reset_index()
                )
                market_re_wide.columns.name = None
                for col in expected_cols:
                    if col not in market_re_wide.columns:
                        market_re_wide[col] = pd.NA

            reinsurance_context = build_reinsurance_view_context(
                selected_wide=re_wide,
                market_wide=market_re_wide,
                selected_company=selected_company,
                selected_line=selected_line,
                minimum_premium=minimum_premium,
            )

            # Recalcular ratios agregados, no sumar ratios
            total_gwp = re_wide["gross_written_premium"].sum()
            total_retained = re_wide["retained_premium"].sum()
            total_ceded = re_wide["reinsurance_ceded_premium"].sum()
            total_paid_claims = re_wide["paid_claims"].sum()

            retention_ratio = total_retained / total_gwp if total_gwp else None
            cession_ratio = total_ceded / total_gwp if total_gwp else None
            paid_claims_ratio = total_paid_claims / total_gwp if total_gwp else None

            col_a, col_b, col_c, col_d = st.columns(4)

            with col_a:
                render_metric_card("Primas emitidas", format_millions(total_gwp))
            with col_b:
                render_metric_card("Primas retenidas", format_millions(total_retained))
            with col_c:
                render_metric_card("Prima cedida reaseguro", format_millions(total_ceded))
            with col_d:
                render_metric_card("Ratio de cesión", format_percentage(cession_ratio))

            col_e, col_f, col_g, col_h = st.columns(4)

            with col_e:
                render_metric_card("Ratio de retención", format_percentage(retention_ratio))
            with col_f:
                render_metric_card("Siniestros pagados", format_millions(total_paid_claims))
            with col_g:
                render_metric_card("Siniestros pagados / primas", format_percentage(paid_claims_ratio))
            with col_h:
                render_metric_card("Registros fuente", f"{len(re_df):,}")

            st.divider()

            render_section_header(
                "Reinsurance Executive Snapshot",
                "Treaty-broker view of ceded premium, retained premium, market benchmark and discussion angles.",
            )

            snapshot_cards = reinsurance_context.get("executive_snapshot", [])
            if snapshot_cards:
                for start in range(0, len(snapshot_cards), 4):
                    card_cols = st.columns(4)
                    for card, column in zip(snapshot_cards[start:start + 4], card_cols):
                        with column:
                            render_metric_card(
                                card.get("label", "Metric"),
                                card.get("value", "N/A"),
                                card.get("detail", ""),
                            )
            else:
                st.warning("Reinsurance indicators are not available for this selection.")

            render_section_header(
                "Company vs Market Benchmark",
                "Comparison against the selected market context using the same year and line filters.",
            )

            benchmark = reinsurance_context.get("market_benchmark", {})
            selected_summary = benchmark.get("selected", {})
            market_summary = benchmark.get("market", {})
            if benchmark.get("available"):
                benchmark_rows = [
                    {
                        "Scope": "Selected company" if selected_company != "TODAS" else "Selected market",
                        "Emitted premium": format_millions(selected_summary.get("gross_written_premium")),
                        "Retained premium": format_millions(selected_summary.get("retained_premium")),
                        "Ceded premium": format_millions(selected_summary.get("reinsurance_ceded_premium")),
                        "Cession ratio": format_percentage(selected_summary.get("cession_ratio")),
                        "Retention ratio": format_percentage(selected_summary.get("retention_ratio")),
                    },
                    {
                        "Scope": "Market benchmark",
                        "Emitted premium": format_millions(market_summary.get("gross_written_premium")),
                        "Retained premium": format_millions(market_summary.get("retained_premium")),
                        "Ceded premium": format_millions(market_summary.get("reinsurance_ceded_premium")),
                        "Cession ratio": format_percentage(market_summary.get("cession_ratio")),
                        "Retention ratio": format_percentage(market_summary.get("retention_ratio")),
                    },
                ]
                render_dataframe(pd.DataFrame(benchmark_rows), width="stretch", hide_index=True)

                if selected_company != "TODAS":
                    diff_col_a, diff_col_b = st.columns(2)
                    with diff_col_a:
                        render_metric_card(
                            "Cession difference vs market",
                            format_percentage(benchmark.get("cession_ratio_difference")),
                            "Selected company minus market benchmark",
                        )
                    with diff_col_b:
                        render_metric_card(
                            "Retention difference vs market",
                            format_percentage(benchmark.get("retention_ratio_difference")),
                            "Selected company minus market benchmark",
                        )
                else:
                    st.info("Company filter is set to TODAS, so this section shows market-level behavior only.")
            else:
                st.warning("Market benchmark is not available for the selected reinsurance filters.")

            render_section_header(
                "Reinsurance by Line",
                "Lines ranked by ceded premium, cession behavior and share of selected ceded premium.",
            )

            by_line = reinsurance_context.get("by_line", pd.DataFrame())
            if by_line is None or by_line.empty:
                st.warning("No line-level reinsurance indicators are available for this selection.")
            else:
                by_line = filter_real_lob_rows(by_line)
                line_chart = by_line.head(15).copy()
                line_chart["ceded_mm"] = line_chart["reinsurance_ceded_premium"] / 1_000_000
                fig_re_line = px.bar(
                    line_chart,
                    x="line_of_business_standard",
                    y="ceded_mm",
                    title="Top lines by ceded premium",
                    labels={
                        "line_of_business_standard": "Line of business",
                        "ceded_mm": "Ceded premium (COP MM)",
                    },
                )
                st.plotly_chart(fig_re_line, width="stretch")

                line_display = by_line.copy()
                for amount_col in [
                    "gross_written_premium",
                    "retained_premium",
                    "reinsurance_ceded_premium",
                    "paid_claims",
                ]:
                    line_display[amount_col] = line_display[amount_col].map(format_millions)
                for ratio_col in [
                    "cession_ratio",
                    "retention_ratio",
                    "paid_claims_ratio",
                    "ceded_share",
                ]:
                    line_display[ratio_col] = line_display[ratio_col].map(format_percentage)
                render_dataframe(
                    line_display[
                        [
                            "line_of_business_standard",
                            "gross_written_premium",
                            "retained_premium",
                            "reinsurance_ceded_premium",
                            "cession_ratio",
                            "retention_ratio",
                            "paid_claims",
                            "paid_claims_ratio",
                            "ceded_share",
                        ]
                    ],
                    width="stretch",
                    hide_index=True,
                )

            render_section_header(
                "Reinsurance Evolution",
                "Ceded premium, retained premium and cession / retention ratios over available years.",
            )

            evolution = reinsurance_context.get("evolution", pd.DataFrame())
            if evolution is None or evolution.empty:
                st.warning("No annual reinsurance evolution is available for this selection.")
            else:
                if evolution["year"].nunique() < 2:
                    st.info(
                        "Only one available year is present in the reinsurance source under the selected filters, "
                        "so year-over-year treaty movement cannot yet be assessed."
                    )
                else:
                    evo_amounts = evolution.melt(
                        id_vars="year",
                        value_vars=["reinsurance_ceded_premium", "retained_premium"],
                        var_name="Metric",
                        value_name="Amount",
                    )
                    evo_amounts["Amount_mm"] = evo_amounts["Amount"] / 1_000_000
                    evo_amounts["Metric"] = evo_amounts["Metric"].map(
                        {
                            "reinsurance_ceded_premium": "Ceded premium",
                            "retained_premium": "Retained premium",
                        }
                    )
                    fig_evo_amounts = px.line(
                        evo_amounts,
                        x="year",
                        y="Amount_mm",
                        color="Metric",
                        markers=True,
                        title="Ceded and retained premium over time",
                        labels={"year": "Year", "Amount_mm": "COP MM"},
                    )
                    st.plotly_chart(fig_evo_amounts, width="stretch")

                    evo_ratios = evolution.melt(
                        id_vars="year",
                        value_vars=["cession_ratio", "retention_ratio"],
                        var_name="Metric",
                        value_name="Ratio",
                    )
                    evo_ratios["Metric"] = evo_ratios["Metric"].map(
                        {
                            "cession_ratio": "Cession ratio",
                            "retention_ratio": "Retention ratio",
                        }
                    )
                    fig_evo_ratios = px.line(
                        evo_ratios,
                        x="year",
                        y="Ratio",
                        color="Metric",
                        markers=True,
                        title="Cession and retention ratio over time",
                        labels={"year": "Year", "Ratio": "Ratio"},
                    )
                    fig_evo_ratios.update_yaxes(tickformat=".1%")
                    st.plotly_chart(fig_evo_ratios, width="stretch")

                evo_display = evolution.copy()
                for amount_col in [
                    "gross_written_premium",
                    "retained_premium",
                    "reinsurance_ceded_premium",
                    "paid_claims",
                ]:
                    evo_display[amount_col] = evo_display[amount_col].map(format_millions)
                for ratio_col in [
                    "cession_ratio",
                    "retention_ratio",
                    "paid_claims_ratio",
                    "ceded_premium_growth",
                    "retained_premium_growth",
                    "cession_ratio_change",
                    "retention_ratio_change",
                ]:
                    if ratio_col in evo_display.columns:
                        evo_display[ratio_col] = evo_display[ratio_col].map(format_percentage)
                render_dataframe(evo_display, width="stretch", hide_index=True)

            render_section_header(
                "Reinsurance Signals",
                "Broker-oriented prompts for treaty discussion. These are discussion signals, not underwriting conclusions.",
            )

            for signal in reinsurance_context.get("signals", []):
                st.markdown(
                    f"**{signal.get('severity', 'Signal')} - {signal.get('title', 'Reinsurance signal')}**  \n"
                    f"{signal.get('explanation', 'No explanation available')}  \n"
                    f"*Broker follow-up:* {signal.get('follow_up', 'Review with the client before formal use.')}"
                )

            render_section_header(
                "Suggested Reinsurance Questions",
                "Practical questions for client or reinsurer conversations based on available structured data.",
            )

            for question in reinsurance_context.get("broker_questions", []):
                st.write(f"- {question}")

            with st.expander("Methodology note", expanded=False):
                st.write(
                    "Reinsurance indicators are based on available Fasecolda - Indicadores de Gestion 2025 "
                    "data normalized in the app database. Cession and retention ratios are recalculated at "
                    "the selected aggregation level and depend on source definitions. This source remains "
                    "exploratory for broker intelligence; figures should be validated before formal client, "
                    "placement, actuarial, or market presentations."
                )

            st.divider()

            st.markdown("### Detailed reinsurance rankings")

            lob_summary = (
                filter_real_lob_rows(re_wide).groupby("line_of_business_standard", as_index=False)
                .agg(
                    gross_written_premium=("gross_written_premium", "sum"),
                    retained_premium=("retained_premium", "sum"),
                    reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
                    paid_claims=("paid_claims", "sum"),
                    companies=("company_standard", "nunique")
                )
            )

            lob_summary["cession_ratio"] = (
                lob_summary["reinsurance_ceded_premium"] / lob_summary["gross_written_premium"]
            )

            lob_summary["retention_ratio"] = (
                lob_summary["retained_premium"] / lob_summary["gross_written_premium"]
            )

            lob_summary["paid_claims_ratio"] = (
                lob_summary["paid_claims"] / lob_summary["gross_written_premium"]
            )

            lob_summary = lob_summary.sort_values("reinsurance_ceded_premium", ascending=False)

            lob_chart = lob_summary.head(20).copy()
            lob_chart["ceded_mm"] = lob_chart["reinsurance_ceded_premium"] / 1_000_000

            fig_ceded_lob = px.bar(
                lob_chart,
                x="line_of_business_standard",
                y="ceded_mm",
                title="Top 20 ramos por prima cedida al reaseguro",
                labels={
                    "line_of_business_standard": "Ramo",
                    "ceded_mm": "Prima cedida en millones de pesos"
                }
            )

            st.plotly_chart(fig_ceded_lob, width="stretch")

            col_1, col_2 = st.columns(2)

            with col_1:
                ratio_chart = lob_summary[
                    lob_summary["gross_written_premium"] >= minimum_premium
                ].sort_values("cession_ratio", ascending=False).head(20)

                fig_cession_ratio = px.bar(
                    ratio_chart,
                    x="line_of_business_standard",
                    y="cession_ratio",
                    title="Top ramos por ratio de cesión",
                    labels={
                        "line_of_business_standard": "Ramo",
                        "cession_ratio": "Ratio de cesión"
                    }
                )

                fig_cession_ratio.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_cession_ratio, width="stretch")

            with col_2:
                retained_chart = lob_summary[
                    lob_summary["gross_written_premium"] >= minimum_premium
                ].sort_values("retention_ratio", ascending=False).head(20)

                fig_retention_ratio = px.bar(
                    retained_chart,
                    x="line_of_business_standard",
                    y="retention_ratio",
                    title="Top ramos por ratio de retención",
                    labels={
                        "line_of_business_standard": "Ramo",
                        "retention_ratio": "Ratio de retención"
                    }
                )

                fig_retention_ratio.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_retention_ratio, width="stretch")

            st.markdown("### Top compañías por prima cedida")

            company_summary_re = (
                re_wide.groupby("company_standard", as_index=False)
                .agg(
                    gross_written_premium=("gross_written_premium", "sum"),
                    retained_premium=("retained_premium", "sum"),
                    reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
                    paid_claims=("paid_claims", "sum")
                )
            )

            company_summary_re["cession_ratio"] = (
                company_summary_re["reinsurance_ceded_premium"] / company_summary_re["gross_written_premium"]
            )

            company_summary_re["retention_ratio"] = (
                company_summary_re["retained_premium"] / company_summary_re["gross_written_premium"]
            )

            company_summary_re = company_summary_re.sort_values("reinsurance_ceded_premium", ascending=False)

            company_chart = company_summary_re.head(20).copy()
            company_chart["ceded_mm"] = company_chart["reinsurance_ceded_premium"] / 1_000_000

            fig_company_ceded = px.bar(
                company_chart,
                x="company_standard",
                y="ceded_mm",
                title="Top 20 compañías por prima cedida al reaseguro",
                labels={
                    "company_standard": "Compañía",
                    "ceded_mm": "Prima cedida en millones de pesos"
                }
            )

            st.plotly_chart(fig_company_ceded, width="stretch")

            st.markdown("### Tabla resumen por ramo")

            lob_display = lob_summary.copy()
            lob_display["gross_written_premium"] = lob_display["gross_written_premium"].map(format_millions)
            lob_display["retained_premium"] = lob_display["retained_premium"].map(format_millions)
            lob_display["reinsurance_ceded_premium"] = lob_display["reinsurance_ceded_premium"].map(format_millions)
            lob_display["paid_claims"] = lob_display["paid_claims"].map(format_millions)
            lob_display["cession_ratio"] = lob_display["cession_ratio"].map(format_percentage)
            lob_display["retention_ratio"] = lob_display["retention_ratio"].map(format_percentage)
            lob_display["paid_claims_ratio"] = lob_display["paid_claims_ratio"].map(format_percentage)

            render_dataframe(
                lob_display[
                    [
                        "line_of_business_standard",
                        "companies",
                        "gross_written_premium",
                        "retained_premium",
                        "reinsurance_ceded_premium",
                        "cession_ratio",
                        "retention_ratio",
                        "paid_claims",
                        "paid_claims_ratio"
                    ]
                ],
                width="stretch"
            )

            st.markdown("### Validación de Indicadores de Gestión 2025")

            if indicadores_validation_df.empty:
                st.warning(
                    "No se encontró reporte de validación de Indicadores de Gestión. "
                    "Ejecuta `python src\\validate_indicadores_gestion_2025.py`."
                )
            else:
                validation_counts_re = indicadores_validation_df["result"].value_counts().reset_index()
                validation_counts_re.columns = ["result", "count"]

                col_v1, col_v2 = st.columns([1, 2])

                with col_v1:
                    render_dataframe(validation_counts_re, width="stretch")

                with col_v2:
                    render_dataframe(indicadores_validation_df, width="stretch")

            if indicadores_validation_flags_df.empty:
                st.info(
                    "No se encontró archivo de flags de Indicadores de Gestión. "
                    "Ejecuta `python src\\validate_indicadores_gestion_2025.py` para generar el detalle."
                )
            else:
                st.markdown("#### Warning counts")
                flags_for_country = indicadores_validation_flags_df.copy()
                if "country" in flags_for_country.columns:
                    flags_for_country = flags_for_country[
                        flags_for_country["country"].astype(str).str.upper() == str(selected_country).upper()
                    ]

                flag_counts = (
                    flags_for_country
                    .groupby(["severity", "flag_name"], as_index=False)
                    .size()
                    .rename(columns={"size": "records"})
                    .sort_values(["severity", "records"], ascending=[True, False])
                )

                render_dataframe(flag_counts, width="stretch")

            st.warning(
                "Metodología: esta vista usa Fasecolda - Indicadores de Gestión 2025. "
                "Los ratios se recalculan a nivel agregado y no se suman. "
                "Los ramos agregados pueden duplicar ramos individuales y deben tratarse con cautela. "
                "La fuente está en validación exploratoria antes de integrarse al core regional principal."
            )
    except Exception as exc:
        render_section_error(exc)


# ============================================================
# TAB 7 â€” DATA STATUS
# ============================================================

if selected_view == "Data Status":
    try:
        validation_df = load_validation_report()
        indicadores_df = load_indicadores_gestion_2025()
        indicadores_validation_df = load_indicadores_gestion_validation()
        indicadores_validation_flags_df = load_indicadores_gestion_validation_flags()
        pipeline_status = load_pipeline_status()
        readiness_df = load_metric_readiness_matrix()
        combined_readiness_df = load_combined_ratio_readiness()
        bridge_summary_df = load_technical_bridge_summary()

        render_section_header(
            "Data Governance Status",
            "Coverage, traceability, mapping readiness and validation warnings for the selected country module.",
        )

        st.info(
            "This Streamlit Cloud demo uses a static DuckDB snapshot included in the demo branch. "
            "Phase 3 adds a manual-run Fasecolda ingestion pipeline, but the app does not execute "
            "that pipeline automatically on launch. Scheduled automation is a future deployment step."
        )
        st.caption(f"Database file in use: {DB_PATH.as_posix()} ({DB_MODE_LABEL})")

        with st.expander("Operational maintenance status", expanded=False):
            st.write("- Data update mode: static demo snapshot.")
            st.write("- Pipeline mode: manual controlled run from CMD or PowerShell.")
            st.write("- Automatic updates: not enabled.")
            st.write("- Candidate database promotion: manual approval only.")
            st.write("- Recommended next step: run controlled monthly updates using the maintenance runbook, then review production scheduling with IT/Data.")

        with st.expander("Deployment diagnostics", expanded=False):
            st.write(f"- build_version = {BUILD_VERSION}")
            st.write(f"- expected_branch = {EXPECTED_BRANCH}")
            st.write(f"- expected_commit_marker = {EXPECTED_COMMIT_MARKER}")
            st.write("- app_file = app/streamlit_app.py")
            st.write("- data_source_expected = Formato 290 / Datos Abiertos e967-4a8r")
            st.write("- expected_filters = Year, Month cutoff, Comparison mode, Company, Line of business")
            st.write("- city_filter_expected = removed")
            st.write(f"- ui_marker = {UI_MARKER}")
            st.write(f"- database_file_in_use = {DB_PATH.as_posix()}")
            st.write(f"- database_mode = {DB_MODE_LABEL}")

        render_section_header(
            "Official Colombia Source - SFC Formato 290",
            "Status of the Datos Abiertos Colombia source-of-truth migration.",
        )
        if formato_290_status.get("available"):
            latest_290 = pd.to_datetime(formato_290_status.get("latest_period"), errors="coerce")
            validation_counts = formato_290_status.get("validation_counts", {}) or {}
            f290_a, f290_b, f290_c, f290_d = st.columns(4)
            with f290_a:
                render_metric_card("Main source", "SFC Formato 290", "Datos Abiertos Colombia ID e967-4a8r")
            with f290_b:
                render_metric_card("Latest period", latest_290.strftime("%d/%m/%Y") if pd.notna(latest_290) else "N/A")
            with f290_c:
                render_metric_card("Rows downloaded", f"{formato_290_status.get('raw_rows') or 0:,}", "Raw API rows")
            with f290_d:
                render_metric_card("Validation", formato_290_status.get("validation_status", "N/A"), "PASS / WARNING / FAIL")

            f290_e, f290_f, f290_g, f290_h = st.columns(4)
            with f290_e:
                render_metric_card("Clean rows", f"{formato_290_status.get('rows') or 0:,}", "Normalized long-form rows")
            with f290_f:
                render_metric_card("Core fact rows", f"{formato_290_status.get('fact_rows') or 0:,}", "Rows used by core dashboard")
            with f290_g:
                render_metric_card("Companies", f"{formato_290_status.get('companies') or 0:,}")
            with f290_h:
                render_metric_card("Ramos", f"{formato_290_status.get('ramos') or 0:,}")

            f290_i, f290_j, f290_k, f290_l = st.columns(4)
            with f290_i:
                render_metric_card(
                    "Core table",
                    "Formato 290" if get_core_market_table_name() == "fact_market_core_formato_290" else "Fallback",
                    "Dashboard source selection",
                )
            with f290_j:
                render_metric_card("Validation PASS", f"{int(validation_counts.get('PASS', 0)):,}")
            with f290_k:
                render_metric_card("Validation WARNING", f"{int(validation_counts.get('WARNING', 0)):,}")
            with f290_l:
                render_metric_card("Extraction", formato_290_status.get("extraction_method") or "N/A")

            f290_m, f290_n, f290_o, f290_p = st.columns(4)
            with f290_m:
                render_metric_card("Available years", "2023, 2024, 2025, 2026")
            with f290_n:
                render_metric_card(
                    "Latest month",
                    latest_290.strftime("%B %Y") if pd.notna(latest_290) else "N/A",
                )
            with f290_o:
                render_metric_card("Comparison mode", comparison_mode)
            with f290_p:
                partial_text = "Yes" if is_formato_290_core and int(selected_month_cutoff or 12) < 12 else "No"
                render_metric_card("Selected year partial", partial_text, comparison_context_label)

            mapped_metrics = ", ".join(formato_290_status.get("mapped_metrics", [])) or "None"
            pending_metrics = ", ".join(formato_290_status.get("pending_metrics", [])) or "None"
            with st.expander("Formato 290 mapping status", expanded=False):
                st.write(f"- Mapped metrics: {mapped_metrics}")
                st.write(f"- Pending/unavailable concepts: {pending_metrics}")
                st.write("- Dashboard written premium: direct written premium + accepted co-insurance + accepted reinsurance premium.")
                st.write("- Dashboard claims: mapped incurred claims / technical account movement.")
                st.write("- Ratios must be calculated from total mapped numerator / total mapped denominator, never by averaging ratios.")
                st.write("- Period basis remains subject to business review before annualizing values.")
                st.write(f"- Last ingestion timestamp: {formato_290_status.get('ingestion_timestamp') or 'N/A'}")
            st.warning(
                "Formato 290 period basis requires business confirmation before annualized growth or full-year comparisons are used."
            )
            st.warning(
                "Negative claims ratios may reflect reserve/recovery/net technical movements and should not be interpreted as ordinary gross loss ratio without validation."
            )
            st.divider()
            render_section_header(
                "Methodology Review",
                "Internal readiness status for Formato 290 insurance metrics before wider broker use.",
            )
            if readiness_df.empty:
                st.warning(
                    "Metric methodology readiness matrix is not available. Run "
                    "`python scripts/build_formato_290_methodology_outputs.py`."
                )
            else:
                status_counts = (
                    readiness_df.groupby(["safe_for_dashboard", "requires_business_review"], as_index=False)
                    .size()
                    .rename(columns={"size": "metrics"})
                )
                method_col_a, method_col_b, method_col_c = st.columns(3)
                with method_col_a:
                    confirmed = readiness_df[
                        (readiness_df["safe_for_dashboard"].astype(str).str.lower() == "yes")
                        & (readiness_df["requires_business_review"].astype(str).str.lower() == "no")
                    ]
                    render_metric_card("Confirmed metrics", f"{len(confirmed):,}", "Directly supported for display")
                with method_col_b:
                    review_needed = readiness_df[
                        readiness_df["requires_business_review"].astype(str).str.lower() == "yes"
                    ]
                    render_metric_card("Requires review", f"{len(review_needed):,}", "Available but method-sensitive")
                with method_col_c:
                    blocked = readiness_df[
                        readiness_df["safe_for_dashboard"].astype(str).str.lower() == "no"
                    ]
                    render_metric_card("Do not show yet", f"{len(blocked):,}", "Not ready for dashboard use")

                review_status = {
                    "Written Premium": "PARTIAL - available, period basis review required",
                    "Claims Methodology": "REQUIRES REVIEW - signed technical claims account",
                    "Reinsurance": "PARTIAL - ceded/retained values available, ratio basis review required",
                    "Commissions / Expenses": "PARTIAL - components available, ratio basis review required",
                    "Technical Result": "CONFIRMED - official UC14 subtotal available",
                    "Combined Ratio": "REQUIRES REVIEW - not ready for display",
                    "Final Combined Ratio": "REQUIRES REVIEW - not ready for display",
                }
                render_dataframe(
                    pd.DataFrame(
                        [{"methodology_area": key, "status": value} for key, value in review_status.items()]
                    ),
                    width="stretch",
                )
                st.info(
                    "Technical Result comes from Formato 290 UC14 / Subcuenta 999. A negative Technical Result "
                    "means the selected company, line or market segment has a negative technical result on that "
                    "technical reporting basis and period; it should not automatically be interpreted as final "
                    "company profit or loss. Technical Result Ratio remains subject to business approval of the "
                    "premium denominator."
                )
                with st.expander("Metric readiness matrix", expanded=False):
                    display_cols = [
                        "metric_name",
                        "available_in_formato_290",
                        "safe_for_dashboard",
                        "requires_business_review",
                        "recommended_label_english",
                        "notes",
                    ]
                    render_dataframe(readiness_df[[col for col in display_cols if col in readiness_df.columns]], width="stretch")
                if not combined_readiness_df.empty:
                    render_section_header(
                        "Combined Ratio / Technical Bridge",
                        "Readiness assessment before any combined ratio is promoted to the main dashboard.",
                    )
                    bridge_col_a, bridge_col_b, bridge_col_c = st.columns(3)
                    if not bridge_summary_df.empty:
                        bridge_row = bridge_summary_df.iloc[0]
                        diff_pct = bridge_row.get("weighted_difference_pct_candidate_2")
                        near_exact_rows = bridge_row.get("near_exact_rows")
                        with bridge_col_a:
                            render_metric_card("Bridge rows", f"{int(bridge_row.get('rows', 0)):,}")
                        with bridge_col_b:
                            render_metric_card("Candidate 2 diff", format_percentage(diff_pct) if pd.notna(diff_pct) else "N/A")
                        with bridge_col_c:
                            render_metric_card("Near-exact rows", f"{int(near_exact_rows or 0):,}", "Difference <= COP 1")
                    render_dataframe(
                        combined_readiness_df[
                            [
                                "ratio_name",
                                "readiness_status",
                                "recommended_dashboard_use",
                                "recommended_label_english",
                                "warning_message",
                            ]
                        ],
                        width="stretch",
                    )
                    st.info(
                        "Technical bridge sample: outputs/reconciliation/formato_290_technical_bridge_sample.csv. "
                        "Combined Ratio remains hidden unless bridge reconciliation and component methodology are approved."
                    )
                st.caption(
                    "Methodology reference: docs/colombia_insurance_metric_methodology.md. "
                    "Latest methodology review timestamp: " + run_time.strftime("%Y-%m-%d %H:%M")
                )
        else:
            st.warning(
                "Formato 290 has not been ingested into DuckDB yet. Core Colombia metrics are still using the "
                "legacy Fasecolda snapshot as an explicit fallback. Run `python scripts/update_formato_290.py` "
                "to create raw, clean, mart and validation tables from Datos Abiertos Colombia."
            )

        render_section_header("Current Data Mode", "Static demo snapshot, manual pipeline metadata and source coverage.")

        status_all_periods_df = load_market_core_all_periods()
        if status_all_periods_df.empty:
            status_country_df = country_df.copy()
        else:
            status_all_periods_df["period_date"] = pd.to_datetime(status_all_periods_df["period_date"], errors="coerce")
            status_all_periods_df["year"] = status_all_periods_df["year"].astype(int)
            status_all_periods_df["month"] = status_all_periods_df["month"].astype(int)
            status_all_periods_df["metric_value"] = pd.to_numeric(status_all_periods_df["metric_value"], errors="coerce")
            status_all_periods_df = normalize_core_market_units(status_all_periods_df)
            status_country_df = status_all_periods_df[status_all_periods_df["country"] == selected_country].copy()
        total_rows = len(status_country_df)
        total_companies = status_country_df["company_standard"].nunique()
        total_lines = status_country_df["line_of_business_standard"].nunique()
        total_cities = status_country_df["city"].nunique()
        total_files = status_country_df["source_file"].nunique()
        min_date = status_country_df["period_date"].min()
        max_date = status_country_df["period_date"].max()
        available_years = sorted(status_country_df["year"].dropna().astype(int).unique())
        available_years_text = (
            f"{min(available_years)}-{max(available_years)}"
            if available_years
            else "N/A"
        )

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            render_metric_card("Loaded records", f"{total_rows:,}", "Core market table")
        with col_b:
            render_metric_card("Companies", f"{total_companies:,}", "Standard company names")
        with col_c:
            render_metric_card("Lines", f"{total_lines:,}", "Standard lines of business")
        with col_d:
            render_metric_card("Source files", f"{total_files:,}", "Processed public files")

        col_e, col_f, col_g, col_h = st.columns(4)

        with col_e:
            render_metric_card("Cities", f"{total_cities:,}", "City-level coverage")
        with col_f:
            render_metric_card("First date", min_date.strftime("%d/%m/%Y") if pd.notna(min_date) else "N/A")
        with col_g:
            render_metric_card("Last date", max_date.strftime("%d/%m/%Y") if pd.notna(max_date) else "N/A")
        with col_h:
            render_metric_card("App review", run_time.strftime("%d/%m/%Y %H:%M"), "Local runtime")

        col_i0, col_j0, col_k0, col_l0 = st.columns(4)

        with col_i0:
            render_metric_card("Available years", available_years_text, "Reporting periods")
        with col_j0:
            render_metric_card("Demo snapshot", "Static", "Streamlit Cloud branch")
        with col_k0:
            render_metric_card(
                "Primary source",
                "SFC Formato 290" if get_core_market_table_name() == "fact_market_core_formato_290" else "Ciudades y Ramos",
                "Datos Abiertos Colombia" if get_core_market_table_name() == "fact_market_core_formato_290" else "Fasecolda public data",
            )
        with col_l0:
            render_metric_card("Auto-update", "Manual only", "Phase 3 pipeline")

        st.divider()

        render_section_header(
            "Regulatory Data Pipeline",
            "Latest manual-run ingestion status, if pipeline metadata has been generated.",
        )

        if pipeline_status:
            pipe_col_a, pipe_col_b, pipe_col_c, pipe_col_d = st.columns(4)
            with pipe_col_a:
                render_metric_card("Last pipeline run", pipeline_status.get("updated_at", "N/A"), "UTC timestamp")
            with pipe_col_b:
                render_metric_card("Mode", pipeline_status.get("mode", "N/A"), "Last executed step")
            with pipe_col_c:
                render_metric_card("Validation", pipeline_status.get("validation_status", "N/A"), "PASS / WARNING / ERROR")
            with pipe_col_d:
                render_metric_card("Database", pipeline_status.get("database_status", "N/A"), "Current DB state")

            pipe_col_e, pipe_col_f, pipe_col_g, pipe_col_h = st.columns(4)
            with pipe_col_e:
                render_metric_card("Discovery", pipeline_status.get("discovery_status", "N/A"), "Source scan status")
            with pipe_col_f:
                render_metric_card("Downloaded", str(pipeline_status.get("files_downloaded", "N/A")), "New source files")
            with pipe_col_g:
                render_metric_card("Processed rows", f"{pipeline_status.get('files_processed', 'N/A')}", "Normalized records")
            with pipe_col_h:
                render_metric_card("Automation", pipeline_status.get("automation_mode", "Manual run only"), "Scheduling status")

            st.caption(pipeline_status.get("message", "Pipeline status metadata loaded."))
        else:
            st.info(
                "No Phase 3 pipeline metadata has been generated yet. The pipeline can be run manually "
                "from CMD with `python -m src.pipeline.run_colombia_pipeline --mode discover` or "
                "`python -m src.pipeline.run_colombia_pipeline --mode validate`."
            )

        st.divider()

        render_section_header("Methodology Limitations", "Core caveats users should keep in mind before using outputs formally.")

        st.info(
            "Core market analytics now prefer SFC Formato 290 when the official regulatory tables "
            "are present in DuckDB. Formato 290 values are reported in pesos except Unidad de Captura "
            "19, which is in COP millions, and Unidad de Captura 20, which is in units. The dashboard "
            "does not apply the old Fasecolda thousands-of-COP conversion to Formato 290 records."
        )

        st.warning(
            "Professional use note: figures are intended for internal market intelligence and broker "
            "meeting preparation. Validate figures against the source files before using them in formal "
            "client, market, actuarial, or financial presentations."
        )

        st.warning(
            "Methodology note: the claims ratio shown in the app is an analytical incurred-claims-over-written-premium "
            "technical movement ratio. It should not be interpreted as ordinary gross siniestralidad, "
            "official technical loss ratio, or combined ratio unless specifically reconciled."
        )

        render_section_header("Data Sources", "Core and complementary sources currently available to the app.")

        source_summary = (
            status_country_df
            .groupby(["country", "regulator", "source"], as_index=False)
            .agg(
                records=("metric_value", "count"),
                files=("source_file", "nunique"),
                first_date=("period_date", "min"),
                last_date=("period_date", "max")
            )
        )

        source_summary["status"] = "Core regional principal"
        source_summary["usage"] = "Prima escrita, siniestros incurridos, resultado técnico, reaseguro, compañías y ramos"

        # Agregar fuente complementaria de Indicadores de Gestión si está cargada
        if "indicadores_df" in globals() and not indicadores_df.empty:
            indicadores_country_df = indicadores_df[indicadores_df["country"] == selected_country].copy()

            if not indicadores_country_df.empty:
                indicadores_country_df["period_date"] = pd.to_datetime(
                    indicadores_country_df["period_date"],
                    errors="coerce"
                )

                indicadores_summary = pd.DataFrame([{
                    "country": selected_country,
                    "regulator": "FASECOLDA",
                    "source": "FASECOLDA - INDICADORES DE GESTION 2025",
                    "records": len(indicadores_country_df),
                    "files": indicadores_country_df["source_file"].nunique(),
                    "first_date": indicadores_country_df["period_date"].min(),
                    "last_date": indicadores_country_df["period_date"].max(),
                    "status": "Fuente complementaria exploratoria",
                    "usage": "Cesión al reaseguro, retención, siniestros pagados, ratios técnicos"
                }])

                source_summary = pd.concat(
                    [source_summary, indicadores_summary],
                    ignore_index=True
                )

        render_dataframe(source_summary, width="stretch")

        st.info(
            "La fuente principal del core Colombia es SFC Formato 290 cuando la tabla regulatoria "
            "está disponible. Indicadores de Gestión 2025 se mantiene como fuente complementaria "
            "exploratoria y requiere validación metodológica antes de cualquier uso formal."
        )

        render_section_header("Mappings Loaded", "Formal mapping tables used for source-to-standard names.")

        mapping_status = build_mapping_status_summary(lob_mapping_df, company_mapping_df)

        map_col_a, map_col_b, map_col_c = st.columns(3)
        map_col_a.metric("dim_line_of_business_mapping rows", f"{mapping_status['lob_rows']:,}")
        map_col_b.metric("dim_company_mapping rows", f"{mapping_status['company_rows']:,}")
        map_col_c.metric("Countries covered", f"{mapping_status['countries']:,}")

        map_col_d, map_col_e, map_col_f = st.columns(3)
        map_col_d.metric("Sources covered", f"{mapping_status['sources']:,}")
        map_col_e.metric("Standard lines of business", f"{mapping_status['standard_lobs']:,}")
        map_col_f.metric("Standard companies", f"{mapping_status['standard_companies']:,}")

        st.write(
            "Los mappings conectan nombres locales de compañías y ramos entre fuentes públicas "
            "con nombres estándar del modelo regional. Esto permite comparar Ciudades y Ramos "
            "con Indicadores de Gestión sin depender de diccionarios internos del app. "
            "Cuando no existe mapping disponible, la vista lo muestra como dato no disponible "
            "en lugar de inventar equivalencias."
        )

        if lob_mapping_df.empty or company_mapping_df.empty:
            st.warning(
                "No mapping available: una o ambas tablas de mapping no están cargadas. "
                "Ejecuta `python src\\load_mappings_to_duckdb.py`."
            )
        else:
            st.success(
                "Mapping status: company and line-of-business mapping tables are available. "
                "They align Fasecolda source names with standard app names."
            )

        render_section_header("Metric Availability", "Available metrics by country, record count and period coverage.")

        available_metrics = (
            status_country_df
            .groupby(["country", "metric_name"], as_index=False)
            .agg(
                records=("metric_value", "count"),
                first_date=("period_date", "min"),
                last_date=("period_date", "max")
            )
        )

        metric_name_display = {
            "gross_written_premium": "Written Premium (Direct + Accepted)",
            "claims": "Incurred Claims / Technical Movement",
            "reinsurance_ceded_premium": "Cesión al reaseguro",
            "technical_result": "Resultado técnico",
            "net_result": "Resultado neto",
            "taxes_or_contributions": "Impuestos / contribuciones"
        }

        available_metrics["metric_display"] = available_metrics["metric_name"].map(metric_name_display).fillna(available_metrics["metric_name"])

        render_dataframe(
            available_metrics[["country", "metric_display", "records", "first_date", "last_date"]],
            width="stretch"
        )

        render_section_header("Processed Source Files", "File-level traceability for the selected country module.")

        files_summary = (
            status_country_df
            .groupby("source_file", as_index=False)
            .agg(
                records=("metric_value", "count"),
                first_date=("period_date", "min"),
                last_date=("period_date", "max")
            )
            .sort_values("source_file")
        )

        render_dataframe(files_summary, width="stretch")

        render_section_header("Validation Checks", "Automated data validation results and warning counts.")

        if validation_df.empty:
            st.warning(
                "No se encontró reporte de validación. Ejecuta `python src\\validate_market_core.py` "
                "para generar `outputs/market_core_validation_report.csv`."
            )
        else:
            validation_counts = validation_df["result"].value_counts().reset_index()
            validation_counts.columns = ["result", "count"]

            col_i, col_j = st.columns([1, 2])

            with col_i:
                render_dataframe(validation_counts, width="stretch")

            with col_j:
                render_dataframe(validation_df, width="stretch")

        render_section_header("Indicadores de Gestión 2025 Validation", "Exploratory reinsurance-source warnings and flags.")

        if indicadores_validation_df.empty:
            st.warning(
                "No se encontró reporte de validación de Indicadores de Gestión. "
                "Ejecuta `python src\\validate_indicadores_gestion_2025.py`."
            )
        else:
            indicadores_validation_counts = indicadores_validation_df["result"].value_counts().reset_index()
            indicadores_validation_counts.columns = ["result", "count"]

            col_k, col_l = st.columns([1, 2])

            with col_k:
                render_dataframe(indicadores_validation_counts, width="stretch")

            with col_l:
                render_dataframe(indicadores_validation_df, width="stretch")

        if indicadores_validation_flags_df.empty:
            st.info("No hay flags detallados cargados para Indicadores de Gestión 2025.")
        else:
            indicadores_flags_status = (
                indicadores_validation_flags_df
                .groupby(["severity", "flag_name"], as_index=False)
                .size()
                .rename(columns={"size": "records"})
                .sort_values(["severity", "records"], ascending=[True, False])
            )
            render_dataframe(indicadores_flags_status, width="stretch")

        st.info(
            "Current version: Colombia Internal v1. This version is suitable for limited internal broker "
            "testing and presentation to a treaty broking team. It is not yet a corporate-hosted "
            "production service. The ingestion pipeline is manual-run only until a scheduling environment "
            "is approved by IT/Data."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 8 â€” REPORTS / EXPORT
# ============================================================

if selected_view == "Reports / Export":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "Export Center",
            "Copy-ready broker outputs and lightweight data exports for meetings, emails, notes and slide preparation.",
        )

        latest_available_year = max(selected_years) if selected_years else "N/A"
        selected_years_label = (
            f"{min(selected_years)}-{max(selected_years)}"
            if selected_years and min(selected_years) != max(selected_years)
            else str(selected_years[0]) if selected_years else "no_year"
        )
        context_col_a, context_col_b, context_col_c, context_col_d = st.columns(4)
        with context_col_a:
            render_metric_card("Country", selected_country, "Current module")
        with context_col_b:
            render_metric_card("Company", selected_company, "Selected filter")
        with context_col_c:
            render_metric_card("Line", "All lines" if selected_line == "TODOS" else selected_line, "Selected filter")
        with context_col_d:
            render_metric_card("Latest year", str(latest_available_year), "Selected years")

        export_metadata = build_export_metadata(
            selected_country,
            selected_company,
            selected_line,
            selected_years,
            generated_at=run_time,
        )

        export_type = st.selectbox(
            "Export type",
            [
                "Company Brief",
                "AI Brief",
                "Reinsurance Summary",
                "Market Summary",
                "Broker One-Pager",
                "PPT-Ready Bullets",
                "Filtered Data",
            ],
            key="reports_export_type",
        )

        report_mapped_company = None
        if selected_company != "TODAS":
            report_mapped_company = map_company_using_mapping_table(
                selected_company,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country,
            )
        report_mapped_line = None
        if selected_line != "TODOS":
            report_mapped_line = map_lob_using_mapping_table(
                selected_line,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country,
            )

        report_reinsurance_wide = build_reinsurance_wide(
            indicadores_df,
            selected_country,
            company=report_mapped_company if selected_company != "TODAS" else None,
            line=report_mapped_line if selected_line != "TODOS" else None,
        )
        report_market_reinsurance_wide = build_reinsurance_wide(
            indicadores_df,
            selected_country,
            line=report_mapped_line if selected_line != "TODOS" else None,
        )
        if not report_reinsurance_wide.empty and "year" in report_reinsurance_wide.columns:
            report_reinsurance_wide = report_reinsurance_wide[
                report_reinsurance_wide["year"].isin(selected_years)
            ].copy()
        if not report_market_reinsurance_wide.empty and "year" in report_market_reinsurance_wide.columns:
            report_market_reinsurance_wide = report_market_reinsurance_wide[
                report_market_reinsurance_wide["year"].isin(selected_years)
            ].copy()

        report_reinsurance_context = build_reinsurance_view_context(
            selected_wide=report_reinsurance_wide,
            market_wide=report_market_reinsurance_wide,
            selected_company=selected_company,
            selected_line=selected_line,
            minimum_premium=minimum_premium,
        )

        report_company_brief = None
        if selected_company != "TODAS":
            report_company_df = filtered_df[filtered_df["company_standard"] == selected_company].copy()
            report_market_reference_df = country_df[country_df["year"].isin(selected_years)].copy()
            if selected_line != "TODOS":
                report_market_reference_df = report_market_reference_df[
                    report_market_reference_df["line_of_business_standard"] == selected_line
                ].copy()
            if selected_city != "TODAS":
                report_market_reference_df = report_market_reference_df[
                    report_market_reference_df["city"] == selected_city
                ].copy()
            report_company_brief = build_company_brief(
                country=selected_country,
                company=selected_company,
                selected_line=selected_line,
                selected_years=selected_years,
                company_df=report_company_df,
                market_df=report_market_reference_df,
                reinsurance_summary=summarize_reinsurance(report_reinsurance_wide),
                minimum_premium=minimum_premium,
                reinsurance_wide=report_reinsurance_wide,
            )

        report_ai_context = build_ai_brief_context(
            market_df=country_df,
            selected_country=selected_country,
            selected_company=selected_company,
            selected_lob=selected_line,
            selected_years=selected_years,
            meeting_purpose="Broker report export",
            brief_type="Pre-meeting company brief",
            indicadores_df=indicadores_df,
            mapped_company=report_mapped_company,
            mapped_line=report_mapped_line,
            minimum_premium=minimum_premium,
            data_status={
                "database_mode": "Candidate local test" if USE_CANDIDATE_DB else "Stable demo",
                "data_update_mode": "Static demo snapshot plus manual pipeline metadata",
            },
        )
        report_ai_markdown = generate_ai_brief_from_context(report_ai_context)

        markdown_exports = {
            "Company Brief": build_export_company_brief_markdown(report_company_brief, export_metadata),
            "AI Brief": build_export_ai_brief_markdown(report_ai_markdown, export_metadata),
            "Reinsurance Summary": build_export_reinsurance_summary_markdown(report_reinsurance_context, export_metadata),
            "Market Summary": build_export_market_summary_markdown(filtered_df, export_metadata, minimum_premium),
            "Broker One-Pager": build_export_broker_one_pager_markdown(
                report_company_brief,
                report_ai_markdown,
                report_reinsurance_context,
                export_metadata,
            ),
            "PPT-Ready Bullets": build_ppt_ready_bullets(
                report_company_brief,
                report_reinsurance_context,
                export_metadata,
            ),
        }

        render_section_header("Preview", "Review the selected export before downloading or copying.")

        if export_type == "Filtered Data":
            render_dataframe(filtered_df.head(1000), width="stretch")
            csv_bytes = dataframe_to_csv_bytes(filtered_df)
            excel_bytes = dataframe_to_excel_bytes(filtered_df, sheet_name="filtered_data")
            filtered_file_base = sanitize_export_filename(
                f"{selected_country}_{selected_company}_{selected_line}_{selected_years_label}_filtered_data"
            )
            data_col_a, data_col_b = st.columns(2)
            with data_col_a:
                st.download_button(
                    label="Download filtered data CSV",
                    data=csv_bytes,
                    file_name=f"{filtered_file_base}.csv",
                    mime="text/csv",
                    key="reports_download_filtered_data_csv",
                )
            with data_col_b:
                if excel_bytes is None:
                    st.info("Excel export is not available in this environment. CSV export is available.")
                else:
                    st.download_button(
                        label="Download filtered data Excel",
                        data=excel_bytes,
                        file_name=f"{filtered_file_base}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="reports_download_filtered_data_excel",
                    )
        else:
            selected_markdown = markdown_exports.get(export_type, "Data not available.")
            if export_type == "PPT-Ready Bullets":
                st.code(selected_markdown, language="markdown")
            else:
                st.markdown(selected_markdown)

            safe_scope = sanitize_export_filename(f"{selected_country}_{selected_company}_{selected_line}_{selected_years_label}_{export_type}")
            markdown_col_a, markdown_col_b = st.columns(2)
            with markdown_col_a:
                st.download_button(
                    label=f"Download {export_type} markdown",
                    data=selected_markdown.encode("utf-8"),
                    file_name=f"{safe_scope}.md",
                    mime="text/markdown",
                    key=f"reports_download_{sanitize_export_filename(export_type)}_md",
                )
            with markdown_col_b:
                html_export = render_markdown_as_html(selected_markdown, title=export_type)
                st.download_button(
                    label=f"Download {export_type} HTML",
                    data=html_export.encode("utf-8"),
                    file_name=f"{safe_scope}.html",
                    mime="text/html",
                    key=f"reports_download_{sanitize_export_filename(export_type)}_html",
                )

        with st.expander("Additional CSV exports", expanded=False):
            csv_col_a, csv_col_b, csv_col_c = st.columns(3)
            with csv_col_a:
                st.download_button(
                    label="Annual summary CSV",
                    data=annual_summary_csv(filtered_df),
                    file_name="annual_market_summary.csv",
                    mime="text/csv",
                    key="reports_download_annual_summary_csv",
                )
            with csv_col_b:
                st.download_button(
                    label="Company summary CSV",
                    data=company_summary_csv(filtered_df),
                    file_name="company_summary.csv",
                    mime="text/csv",
                    key="reports_download_company_summary_csv",
                )
            with csv_col_c:
                st.download_button(
                    label="Reinsurance summary CSV",
                    data=reinsurance_summary_csv(indicadores_df, selected_country),
                    file_name="reinsurance_summary.csv",
                    mime="text/csv",
                    key="reports_download_reinsurance_summary_csv",
                )

        st.warning(
            "Export methodology: Incurred Claims / Written Premium is analytical and not necessarily official technical "
            "siniestralidad or combined ratio. Reinsurance indicators are exploratory. External intelligence "
            "is curated/manual and may be empty. Validate figures before formal client or market presentations."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 9 â€” DATA TABLE
# ============================================================

if selected_view == "Data Table":
    try:
        render_section_header(
            "Data Table",
            "Inspect the first 1,000 filtered records for traceability and internal analysis.",
        )

        render_dataframe(
            filtered_df.head(1000),
            width="stretch"
        )

        render_section_header("Dataset Description", "Core market records loaded into the regional DuckDB model.")

        st.write(
            """
            This module uses public Fasecolda data on premiums and claims. The data has been
            consolidated, normalized and loaded into DuckDB under the regional `fact_market_core`
            structure.

            Colombia is the first operating country module in the LAC Insurance Market Intelligence Hub.
            The architecture is designed to support future Latin America and Caribbean expansion, while
            preserving clear source, period and methodology traceability.
            """
        )
    except Exception as exc:
        render_section_error(exc)

