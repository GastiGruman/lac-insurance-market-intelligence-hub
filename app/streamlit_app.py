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
    inject_global_css,
    render_metric_card,
    render_section_header,
    render_sidebar_label,
    render_status_pill,
    render_top_header,
)

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="LAC Insurance Market Intelligence Hub",
    layout="wide"
)

inject_global_css()
configure_plotly_theme()

APP_NAME = "LAC Insurance Market Intelligence Hub"
COUNTRY_MODULE = "Colombia country module"
USE_CANDIDATE_DB = os.getenv("USE_CANDIDATE_DB", "false").strip().lower() in {"1", "true", "yes", "y"}
DB_PATH = (
    Path("data/database/insurance_market_candidate.duckdb")
    if USE_CANDIDATE_DB
    else Path("data/database/insurance_market.duckdb")
)
VALIDATION_REPORT_PATH = Path("outputs/market_core_validation_report.csv")
INDICADORES_VALIDATION_REPORT_PATH = Path("outputs/indicadores_gestion_2025_validation_report.csv")
INDICADORES_VALIDATION_FLAGS_PATH = Path("outputs/indicadores_gestion_2025_flags.csv")
PIPELINE_STATUS_PATH = Path("data/metadata/latest_pipeline_status.json")
CORE_MARKET_SOURCE = "FASECOLDA - CIUDADES Y RAMOS"
CORE_SOURCE_VALUE_MULTIPLIER = 1_000
DEBUG_MODE = False
CLAIMS_PREMIUM_RATIO_LABEL_ES = "Siniestros / Primas"
CLAIMS_PREMIUM_RATIO_LABEL_EN = "Claims / Premiums"
CLAIMS_PREMIUM_RATIO_NOTE = (
    "The 'Claims / Premiums' ratio is an analytical metric calculated from the available "
    "app database. It may not be equivalent to Fasecolda's official technical loss ratio, "
    "combined ratio, or other technical indicators, which may use different premium, "
    "claims, reserve, commission, and expense bases."
)
CLAIMS_PREMIUM_RATIO_NOTE_ES = (
    "El ratio 'Siniestros / Primas' corresponde a una metrica analitica calculada con "
    "la informacion disponible en la base de la app. No necesariamente equivale a la "
    "siniestralidad tecnica oficial, indice combinado u otros indicadores tecnicos "
    "publicados por Fasecolda, que pueden usar bases de prima, siniestros, reservas, "
    "comisiones y gastos diferentes."
)

# ============================================================
# FUNCIONES DE CARGA
# ============================================================

@st.cache_data
def load_market_core():
    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return conn.execute("""
            WITH latest_months AS (
                SELECT country, source, year, MAX(month) AS month
                FROM fact_market_core
                GROUP BY country, source, year
            )
            SELECT f.*
            FROM fact_market_core f
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

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return conn.execute("""
            SELECT *
            FROM fact_market_core
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


def warn_and_stop(message):
    st.warning(message)
    st.stop()


def safe_has_columns(data, required_columns):
    return isinstance(data, pd.DataFrame) and set(required_columns).issubset(data.columns)


def safe_divide(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return None
    return numerator / denominator


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
    fig.update_xaxes(
        tickmode="array",
        tickvals=years,
        tickformat="d"
    )
    return fig


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
        "TOTAL DAÑOS",
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
        "SUSTRACCION": "Sustracción",
        "SUSTRACCIÓN": "Sustracción",
        "DESEMPLEO": "Desempleo",
        "EXEQUIAS": "Exequias",
        "MANEJO": "Manejo",
        "CORRIENTE DEBIL": "Corriente Débil",
        "CORRIENTE DÉBIL": "Corriente Débil",
        "SEGUROS DE CREDITO": "Seguros de Credito",
        "SEGUROS DE CRÉDITO": "Seguros de Credito",
        "MINAS Y PETROLEOS": "Minas y Petróleos",
        "MINAS Y PETRÓLEOS": "Minas y Petróleos",
        "MONTAJE Y ROTURA": "Montaje y Rotura",
        "INGENIERIA": "Ingenieria",
        "INGENIERÍA": "Ingenieria",
        "TODO RIESGO CONTRATISTA": "Todo Riesgo Cont.",
        "NAVEGACION Y CASCO": "Nav.yCasco",
        "NAVEGACIÓN Y CASCO": "Nav.yCasco",
        "VIDRIOS": "Vidrios",
        "DECENAL": "Decenal",
        "BEPS": "BEPS",
        "ACCIDENTES PERSONALES": "Accidentes P",
        "ACCIDENTES P": "Accidentes P",
        "OTROS DAÑOS": "Otros Daños",
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

    summary["siniestros"] = summary["siniestros"].fillna(0)
    summary["siniestralidad"] = summary["siniestros"] / summary["primas"]

    return summary


def make_display_summary(summary_df):
    display_df = summary_df.copy()

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
        f"¿Hay algún ramo donde el ratio siniestros / primas de {company_name} esté generando presión técnica?",
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
# CARGA Y NORMALIZACIÓN DE DATOS
# ============================================================

df = load_market_core()
lob_mapping_df = load_lob_mapping()
company_mapping_df = load_company_mapping()

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
analysis_df = df.copy()

last_update = df["period_date"].max()
analysis_last_update = analysis_df["period_date"].max()
run_time = datetime.now()

# ============================================================
# HEADER
# ============================================================

render_top_header(
    APP_NAME,
    "Professional market intelligence for reinsurance brokers. Colombia is the first country module in a regional platform built around public market data, technical signals, broker briefs, AI assistance, and news monitoring.",
    kicker="Regional by design. Colombia-rich where possible. Broker-focused always.",
)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## Market Intelligence")
st.sidebar.caption("Internal broker analytics platform")
st.sidebar.divider()

render_sidebar_label("Navigation")
st.sidebar.caption("Use the top tabs to move between market dashboard, company brief, AI, news, data status and exports.")

render_sidebar_label("Market scope")

country_options = sorted(analysis_df["country"].dropna().unique())
if not country_options:
    warn_and_stop("Data not available for the selected source.")

selected_country = st.sidebar.selectbox(
    "Country",
    country_options,
    index=0
)

country_df = analysis_df[analysis_df["country"] == selected_country]

years = sorted(country_df["year"].dropna().unique())
if not years:
    warn_and_stop("Data not available for the selected country.")

selected_years = st.sidebar.multiselect(
    "Years",
    years,
    default=years
)

if not selected_years:
    warn_and_stop("Please select at least one year to continue.")

render_sidebar_label("Portfolio filters")

company_options = ["TODAS"] + sorted(country_df["company_standard"].dropna().unique())
selected_company = st.sidebar.selectbox(
    "Company",
    company_options
)

line_options = ["TODOS"] + sorted(country_df["line_of_business_standard"].dropna().unique())
selected_line = st.sidebar.selectbox(
    "Line of business",
    line_options
)

city_options = ["TODAS"] + sorted(country_df["city"].dropna().unique())
selected_city = st.sidebar.selectbox(
    "City",
    city_options
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

render_sidebar_label("Current module")
st.sidebar.write(f"**{selected_country} country module**")
st.sidebar.caption("Version: Colombia MVP Demo")
st.sidebar.caption("Phase: 4E - Broker reports and export center")
st.sidebar.caption("Data update mode: Static demo snapshot plus manual pipeline metadata")
st.sidebar.caption("Automatic updates: Manual-run pipeline available; scheduling not yet enabled")
st.sidebar.caption(f"Database mode: {'Candidate local test' if USE_CANDIDATE_DB else 'Stable demo'}")
st.sidebar.caption("Data model: Regional Market Core")
st.sidebar.caption("Primary source: Fasecolda - Ciudades y Ramos")
st.sidebar.caption("Annual views use the latest available monthly cut per year.")

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
    warn_and_stop(
        "No data available for the selected filters. Please adjust your selection."
    )

premium_df = filtered_df[filtered_df["metric_name"] == "gross_written_premium"]
claims_df = filtered_df[filtered_df["metric_name"] == "claims"]

total_premium = premium_df["metric_value"].sum()
total_claims = claims_df["metric_value"].sum()
loss_ratio = safe_divide(total_claims, total_premium)

# ============================================================
# KPIs PRINCIPALES
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_metric_card("Premiums", format_millions(total_premium), "Gross written premium")
with col2:
    render_metric_card("Claims", format_millions(total_claims), "Reported claims")
with col3:
    render_metric_card(CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(loss_ratio), "Analytical claims-to-premium ratio")
with col4:
    render_metric_card("Filtered records", f"{len(filtered_df):,}", "Current selection")

st.caption(
    f"Selected country: {selected_country} | "
    f"Primary source: Fasecolda - Ciudades y Ramos | "
    f"Analytics use the latest available monthly cut per year | "
    f"Source values converted from thousands of COP to COP | "
    f"Last available dataset date: "
    f"{analysis_last_update.strftime('%d/%m/%Y') if pd.notna(analysis_last_update) else 'N/A'}"
)

st.info(CLAIMS_PREMIUM_RATIO_NOTE)

st.divider()

# ============================================================
# LAZY NAVIGATION
# ============================================================

PAGE_OPTIONS = [
    "Market Overview",
    "Company Explorer",
    "Line of Business Explorer",
    "Company Brief",
    "AI Brief",
    "News",
    "Technical Signals",
    "Reinsurance View",
    "Data Status",
    "Reports / Export",
    "Data Table",
]

selected_view = st.radio(
    "Navigation",
    PAGE_OPTIONS,
    horizontal=True,
    label_visibility="collapsed",
    key="main_navigation",
)

# ============================================================
# TAB 1 — MARKET OVERVIEW
# ============================================================

if selected_view == "Market Overview":
    try:
        render_section_header(
            "Executive Market Dashboard",
            "A broker-focused view of premiums, claims, claims-to-premium ratio, market movement, and portfolio concentration under the selected filters.",
        )

        action_col_a, action_col_b, action_col_c = st.columns(3)
        with action_col_a:
            render_metric_card("Key action", "Market Dashboard", "Review the trend charts below")
        with action_col_b:
            render_metric_card("Key action", "Company Brief", "Select a company in the sidebar")
        with action_col_c:
            render_metric_card("Key action", "Data Status", "Validate coverage and warnings")

        render_section_header("Market Trends", "Premiums, claims and claims-to-premium ratio for the selected market scope.")

        year_summary = (
            filtered_df
            .groupby(["year", "metric_name"], as_index=False)["metric_value"]
            .sum()
        )

        year_summary["value_mm"] = year_summary["metric_value"] / 1_000_000

        metric_labels = {
            "gross_written_premium": "Primas",
            "claims": "Siniestros"
        }

        year_summary["metric_label"] = year_summary["metric_name"].map(metric_labels)

        fig_year = px.line(
            year_summary,
            x="year",
            y="value_mm",
            color="metric_label",
            markers=True,
            title="Evolución de primas y siniestros",
            labels={
                "year": "Año",
                "value_mm": "Valor en millones de pesos",
                "metric_label": "Métrica"
            }
        )

        fix_year_axis(fig_year, year_summary["year"].unique())
        st.plotly_chart(fig_year, width="stretch")

        yearly_lr = prepare_premium_claims_summary(filtered_df, ["year"])
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
                title=f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} anual",
                labels={
                    "year": "Año",
                    "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                }
            )

            fix_year_axis(fig_lr, yearly_lr["year"].unique())
            fig_lr.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_lr, width="stretch")

        with col_b:
            fig_growth = px.bar(
                yearly_lr,
                x="year",
                y="premium_growth",
                title="Crecimiento anual de primas",
                labels={
                    "year": "Año",
                    "premium_growth": "Crecimiento"
                }
            )

            fix_year_axis(fig_growth, yearly_lr["year"].unique())
            fig_growth.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_growth, width="stretch")

        st.subheader("Resumen anual")

        yearly_display = make_display_summary(yearly_lr)
        st.dataframe(
            yearly_display[["year", "primas", "siniestros", CLAIMS_PREMIUM_RATIO_LABEL_ES, "premium_growth"]],
            width="stretch"
        )

        st.subheader("Ranking de mercado")

        col_c, col_d = st.columns(2)

        with col_c:
            premium_by_company = (
                premium_df
                .groupby("company_standard", as_index=False)["metric_value"]
                .sum()
                .sort_values("metric_value", ascending=False)
                .head(15)
            )

            premium_by_company["value_mm"] = premium_by_company["metric_value"] / 1_000_000

            fig_company = px.bar(
                premium_by_company,
                x="company_standard",
                y="value_mm",
                title="Top 15 compañías por primas",
                labels={
                    "company_standard": "Compañía",
                    "value_mm": "Primas en millones de pesos"
                }
            )

            st.plotly_chart(fig_company, width="stretch")

        with col_d:
            premium_by_line = (
                premium_df
                .groupby("line_of_business_standard", as_index=False)["metric_value"]
                .sum()
                .sort_values("metric_value", ascending=False)
                .head(15)
            )

            premium_by_line["value_mm"] = premium_by_line["metric_value"] / 1_000_000

            fig_line = px.bar(
                premium_by_line,
                x="line_of_business_standard",
                y="value_mm",
                title="Top 15 ramos por primas",
                labels={
                    "line_of_business_standard": "Ramo",
                    "value_mm": "Primas en millones de pesos"
                }
            )

            st.plotly_chart(fig_line, width="stretch")

        st.subheader("Market share por compañía")

        market_share = (
            premium_df
            .groupby("company_standard", as_index=False)["metric_value"]
            .sum()
            .sort_values("metric_value", ascending=False)
        )

        if not market_share.empty and market_share["metric_value"].sum() > 0:
            market_share["market_share"] = market_share["metric_value"] / market_share["metric_value"].sum()
            market_share_top = market_share.head(15)

            fig_share = px.bar(
                market_share_top,
                x="company_standard",
                y="market_share",
                title="Top 15 compañías por participación de mercado",
                labels={
                    "company_standard": "Compañía",
                    "market_share": "Market share"
                }
            )

            fig_share.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_share, width="stretch")
        else:
            st.info("No hay primas suficientes para calcular market share.")
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 2 — COMPANY EXPLORER
# ============================================================

if selected_view == "Company Explorer":
    try:
        st.subheader("Company Explorer")
        st.caption("Análisis específico de una aseguradora.")

        if selected_company == "TODAS":
            st.info("Selecciona una compañía en el filtro lateral para ver el análisis específico.")
        else:
            company_df = filtered_df[filtered_df["company_standard"] == selected_company]

            company_summary = prepare_premium_claims_summary(company_df, ["year"])
            company_summary["premium_growth"] = company_summary["primas"].pct_change()
            company_summary["primas_mm"] = company_summary["primas"] / 1_000_000
            company_summary["siniestros_mm"] = company_summary["siniestros"] / 1_000_000

            latest_company_year = int(company_summary["year"].max()) if not company_summary.empty else None

            if latest_company_year:
                latest_company_row = company_summary[company_summary["year"] == latest_company_year]
                latest_company_premium = latest_company_row["primas"].sum()
                latest_company_claims = latest_company_row["siniestros"].sum()
                latest_company_lr = (
                    latest_company_claims / latest_company_premium
                    if latest_company_premium else None
                )

                k1, k2, k3 = st.columns(3)
                k1.metric("Primas último año", format_millions(latest_company_premium))
                k2.metric("Siniestros último año", format_millions(latest_company_claims))
                k3.metric(f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} último año", format_percentage(latest_company_lr))

            col_a, col_b = st.columns(2)

            with col_a:
                fig_company_premium = px.line(
                    company_summary,
                    x="year",
                    y="primas_mm",
                    markers=True,
                    title=f"Primas anuales — {selected_company}",
                    labels={
                        "year": "Año",
                        "primas_mm": "Primas en millones de pesos"
                    }
                )

                fix_year_axis(fig_company_premium, company_summary["year"].unique())
                st.plotly_chart(fig_company_premium, width="stretch")

            with col_b:
                fig_company_lr = px.line(
                    company_summary,
                    x="year",
                    y="siniestralidad",
                    markers=True,
                    title=f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} anual — {selected_company}",
                    labels={
                        "year": "Año",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                    }
                )

                fix_year_axis(fig_company_lr, company_summary["year"].unique())
                fig_company_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_company_lr, width="stretch")

            st.subheader("Principales ramos de la compañía")

            company_premium = company_df[company_df["metric_name"] == "gross_written_premium"]

            company_by_line = (
                company_premium
                .groupby("line_of_business_standard", as_index=False)["metric_value"]
                .sum()
                .sort_values("metric_value", ascending=False)
                .head(15)
            )

            company_by_line["value_mm"] = company_by_line["metric_value"] / 1_000_000

            fig_company_line = px.bar(
                company_by_line,
                x="line_of_business_standard",
                y="value_mm",
                title=f"Top ramos por primas — {selected_company}",
                labels={
                    "line_of_business_standard": "Ramo",
                    "value_mm": "Primas en millones de pesos"
                }
            )

            st.plotly_chart(fig_company_line, width="stretch")

            st.subheader("Resumen anual de la compañía")

            company_display = make_display_summary(company_summary)
            st.dataframe(
                company_display[["year", "primas", "siniestros", CLAIMS_PREMIUM_RATIO_LABEL_ES, "premium_growth"]],
                width="stretch"
            )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 3 — LINE OF BUSINESS EXPLORER
# ============================================================

if selected_view == "Line of Business Explorer":
    try:
        st.subheader("Line of Business Explorer")
        st.caption("Análisis específico de un ramo.")

        if selected_line == "TODOS":
            st.info("Selecciona un ramo en el filtro lateral para ver el análisis específico.")
        else:
            line_df = filtered_df[filtered_df["line_of_business_standard"] == selected_line]

            line_summary = prepare_premium_claims_summary(line_df, ["year"])
            line_summary["premium_growth"] = line_summary["primas"].pct_change()
            line_summary["primas_mm"] = line_summary["primas"] / 1_000_000
            line_summary["siniestros_mm"] = line_summary["siniestros"] / 1_000_000

            col_a, col_b = st.columns(2)

            with col_a:
                fig_line_premium = px.line(
                    line_summary,
                    x="year",
                    y="primas_mm",
                    markers=True,
                    title=f"Primas anuales — {selected_line}",
                    labels={
                        "year": "Año",
                        "primas_mm": "Primas en millones de pesos"
                    }
                )

                fix_year_axis(fig_line_premium, line_summary["year"].unique())
                st.plotly_chart(fig_line_premium, width="stretch")

            with col_b:
                fig_line_lr = px.line(
                    line_summary,
                    x="year",
                    y="siniestralidad",
                    markers=True,
                    title=f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} anual — {selected_line}",
                    labels={
                        "year": "Año",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                    }
                )

                fix_year_axis(fig_line_lr, line_summary["year"].unique())
                fig_line_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_line_lr, width="stretch")

            st.subheader("Top compañías dentro del ramo")

            line_premium = line_df[line_df["metric_name"] == "gross_written_premium"]

            line_by_company = (
                line_premium
                .groupby("company_standard", as_index=False)["metric_value"]
                .sum()
                .sort_values("metric_value", ascending=False)
                .head(20)
            )

            line_by_company["value_mm"] = line_by_company["metric_value"] / 1_000_000

            fig_line_company = px.bar(
                line_by_company,
                x="company_standard",
                y="value_mm",
                title=f"Top compañías por primas — {selected_line}",
                labels={
                    "company_standard": "Compañía",
                    "value_mm": "Primas en millones de pesos"
                }
            )

            st.plotly_chart(fig_line_company, width="stretch")

            st.subheader(f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} por compañía en el ramo")

            line_company_lr = prepare_premium_claims_summary(line_df, ["company_standard"])
            line_company_lr = line_company_lr[line_company_lr["primas"] >= minimum_premium]
            line_company_lr = line_company_lr.sort_values("primas", ascending=False).head(20)
            line_company_lr["primas_mm"] = line_company_lr["primas"] / 1_000_000

            if not line_company_lr.empty:
                fig_line_company_lr = px.bar(
                    line_company_lr,
                    x="company_standard",
                    y="siniestralidad",
                    title=f"{CLAIMS_PREMIUM_RATIO_LABEL_ES} por compañía — {selected_line}",
                    labels={
                        "company_standard": "Compañía",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                    },
                    hover_data=["primas_mm"]
                )

                fig_line_company_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_line_company_lr, width="stretch")
            else:
                st.info("No hay compañías que superen el umbral mínimo de primas seleccionado.")

            st.subheader("Resumen anual del ramo")

            line_display = make_display_summary(line_summary)
            st.dataframe(
                line_display[["year", "primas", "siniestros", CLAIMS_PREMIUM_RATIO_LABEL_ES, "premium_growth"]],
                width="stretch"
            )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 4 — COMPANY BRIEF
# ============================================================

if selected_view == "Company Brief":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "Executive Broker Briefing",
            "Structured meeting preparation generated from the selected filters and public structured market data.",
        )

        if selected_company == "TODAS":
            st.info("Selecciona una compañía en el filtro lateral para generar el Company Brief.")
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

            render_section_header(
                "Executive Snapshot",
                "Compact view of market position, portfolio focus, growth, Claims / Premiums and broker angle.",
            )
            snapshot_items = brief.get("executive_snapshot", [])
            if snapshot_items:
                for start in range(0, len(snapshot_items), 4):
                    snapshot_cols = st.columns(4)
                    for col, item in zip(snapshot_cols, snapshot_items[start:start + 4]):
                        with col:
                            render_metric_card(
                                item.get("label", "Metric"),
                                item.get("value", "N/A"),
                                item.get("detail", "Not enough data available for this metric."),
                            )
            else:
                st.info("Not enough data available for the executive snapshot.")

            col_a, col_b = st.columns([2, 1])

            with col_a:
                render_section_header("Executive Narrative")
                st.write(brief["executive_summary"])

                render_section_header("Market Position", "Premium ranking, market share and comparison with the selected market.")
                market_position = brief.get("market_position", {})
                position_cols = st.columns(4)
                with position_cols[0]:
                    rank_value = (
                        f"#{int(market_position['rank'])}"
                        if pd.notna(market_position.get("rank", pd.NA))
                        else "N/A"
                    )
                    render_metric_card("Rank", rank_value, "By premium in selected market")
                with position_cols[1]:
                    render_metric_card("Market share", format_percentage(market_position.get("market_share", pd.NA)))
                with position_cols[2]:
                    render_metric_card("Company premium", format_millions(market_position.get("company_premium", pd.NA)))
                with position_cols[3]:
                    render_metric_card("Market premium", format_millions(market_position.get("market_premium", pd.NA)))

                top_companies = market_position.get("top_companies", pd.DataFrame())
                if isinstance(top_companies, pd.DataFrame) and not top_companies.empty:
                    top_companies_chart = top_companies.copy()
                    top_companies_chart["premium_mm"] = top_companies_chart["primas"] / 1_000_000
                    fig_top_market = px.bar(
                        top_companies_chart,
                        x="company_standard",
                        y="premium_mm",
                        title=f"Top 5 companies by premium — {market_position.get('latest_year', 'selected year')}",
                        labels={
                            "company_standard": "Company",
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
                    st.dataframe(
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

                render_section_header("Technical Performance", "Premium, claims and claims-to-premium ratio evolution.")
                premium_evolution = brief["premium_evolution"].copy()
                if not premium_evolution.empty:
                    premium_evolution["primas_display"] = premium_evolution["primas"].map(format_millions)
                    premium_evolution["siniestros_display"] = premium_evolution["siniestros"].map(format_millions)
                    premium_evolution["siniestralidad_display"] = premium_evolution["siniestralidad"].map(format_percentage)
                    premium_evolution["premium_growth_display"] = premium_evolution["premium_growth"].map(format_percentage)
                    premium_evolution_display = premium_evolution.rename(
                        columns={"siniestralidad_display": CLAIMS_PREMIUM_RATIO_LABEL_ES}
                    )
                    st.dataframe(
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
                    st.dataframe(
                        market_share_display[
                            ["year", "company_premium", "market_premium", "market_share_display"]
                        ],
                        width="stretch"
                    )

                render_section_header("Portfolio Mix", "Top lines, portfolio share, Claims / Premiums and growth.")
                st.caption(brief.get("portfolio_interpretation", "Not enough data available for portfolio interpretation."))
                portfolio_display = brief.get("portfolio_mix", pd.DataFrame()).copy()
                if portfolio_display.empty:
                    st.info("Data not available")
                else:
                    portfolio_display["premium_display"] = portfolio_display["primas"].map(format_millions)
                    portfolio_display["portfolio_share_display"] = portfolio_display["portfolio_share"].map(format_percentage)
                    portfolio_display["claims_premiums_display"] = portfolio_display["siniestralidad"].map(format_percentage)
                    portfolio_display["premium_growth_display"] = portfolio_display["premium_growth"].map(format_percentage)
                    st.dataframe(
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
                            title="Claims / Premiums evolution",
                            labels={"year": "Year", "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_EN},
                        )
                        fix_year_axis(fig_ratio, evolution_chart["year"].unique())
                        fig_ratio.update_yaxes(tickformat=".1%")
                        st.plotly_chart(fig_ratio, width="stretch")
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

                render_section_header("Growth Signals", "Lines with material growth or changing Claims / Premiums.")
                growth_display = brief.get("growth_signals", pd.DataFrame()).copy()
                if growth_display.empty:
                    st.info("Data not available")
                else:
                    growth_display["primas_display"] = growth_display["primas"].map(format_millions)
                    growth_display["premium_growth_display"] = growth_display["premium_growth"].map(format_percentage)
                    growth_display["claims_premiums_change_display"] = growth_display["claims_premiums_change"].map(format_percentage)
                    st.dataframe(
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

                render_section_header("Claims / Premiums Watch", "Lines with deteriorating analytical claims-to-premium ratio.")
                deterioration_display = brief["deteriorating_loss_ratio_lines"].copy()
                if deterioration_display.empty:
                    st.info("Data not available")
                else:
                    deterioration_display["siniestralidad_display"] = deterioration_display["siniestralidad"].map(format_percentage)
                    deterioration_display["loss_ratio_change_display"] = deterioration_display["loss_ratio_change"].map(format_percentage)
                    deterioration_display = deterioration_display.rename(
                        columns={
                            "siniestralidad_display": CLAIMS_PREMIUM_RATIO_LABEL_ES,
                            "loss_ratio_change_display": "Change in Claims / Premiums",
                        }
                    )
                    st.dataframe(
                        deterioration_display[
                            [
                                "line_of_business_standard",
                                "year",
                                CLAIMS_PREMIUM_RATIO_LABEL_ES,
                                "Change in Claims / Premiums",
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
                        st.dataframe(
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

            with col_b:
                render_section_header("Quick Indicators")

                company_summary = prepare_premium_claims_summary(company_df, ["year"])

                if not company_summary.empty:
                    latest_year = int(company_summary["year"].max())
                    latest_row = company_summary[company_summary["year"] == latest_year]

                    latest_premium = latest_row["primas"].sum()
                    latest_claims = latest_row["siniestros"].sum()
                    latest_lr = latest_claims / latest_premium if latest_premium else None

                    render_metric_card("Year", str(latest_year))
                    render_metric_card("Premiums", format_millions(latest_premium))
                    render_metric_card("Claims", format_millions(latest_claims))
                    render_metric_card(CLAIMS_PREMIUM_RATIO_LABEL_EN, format_percentage(latest_lr))

                if company_reinsurance_summary.get("available"):
                    render_section_header("Reinsurance")
                    render_metric_card("Cession ratio", format_percentage(company_reinsurance_summary["cession_ratio"]))
                    render_metric_card("Retention ratio", format_percentage(company_reinsurance_summary["retention_ratio"]))
                    render_metric_card("Ceded premium", format_millions(company_reinsurance_summary["reinsurance_ceded_premium"]))
                else:
                    st.info("Reinsurance indicators not available for this selection.")

                render_section_header("Data Source")
                st.write(f"Source: {brief['source']['source']}")
                st.write(f"Period: {brief['source']['period']}")
                st.write(f"Records: {brief['source']['records']:,}")

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
                "Claims / Premiums is an analytical claims-to-premium ratio, not necessarily Fasecolda's "
                "official technical loss ratio or combined ratio. Indicadores de Gestion 2025 remains "
                "exploratory and figures should be validated before formal client or market use."
            )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 5 — AI BRIEF
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
            "news, ratings, financial statements, leadership/key people or live web search. Claims / Premiums "
            "is analytical, not necessarily official technical siniestralidad or combined ratio. Reinsurance "
            "indicators remain exploratory where source limitations apply."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 6 — NEWS
# ============================================================

if selected_view == "News":
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
            st.warning("No curated news available for the selected company yet.")
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
                st.info("No manually curated leadership data is available for the selected company.")
            else:
                st.dataframe(people_df, width="stretch", hide_index=True)

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
# TAB 7 — TECHNICAL SIGNALS
# ============================================================

if selected_view == "Technical Signals":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        st.subheader("Technical Signals")
        st.caption("Broker-focused signals for market monitoring and meeting preparation.")

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
            st.info("Data not available for technical signals under the selected filters.")
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
            st.dataframe(
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
                st.dataframe(
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

        st.markdown("### Compañías con mayor crecimiento anual de primas")

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
                title=f"Top crecimiento de primas por compañía — {latest_year}",
                labels={
                    "company_standard": "Compañía",
                    "premium_growth": "Crecimiento"
                }
            )

            fig_top_growth.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_top_growth, width="stretch")
        else:
            st.info("No hay datos suficientes para mostrar crecimiento con el umbral seleccionado.")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"### Compañías con mayor {CLAIMS_PREMIUM_RATIO_LABEL_ES.lower()}")

            company_lr = prepare_premium_claims_summary(filtered_df, ["company_standard"])
            company_lr = company_lr[company_lr["primas"] >= minimum_premium]
            company_lr = company_lr.sort_values("siniestralidad", ascending=False).head(15)
            company_lr["primas_mm"] = company_lr["primas"] / 1_000_000

            if not company_lr.empty:
                fig_company_high_lr = px.bar(
                    company_lr,
                    x="company_standard",
                    y="siniestralidad",
                    title=f"Top compañías por {CLAIMS_PREMIUM_RATIO_LABEL_ES.lower()}",
                    labels={
                        "company_standard": "Compañía",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                    },
                    hover_data=["primas_mm"]
                )

                fig_company_high_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_company_high_lr, width="stretch")
            else:
                st.info("No hay compañías que superen el umbral mínimo de primas seleccionado.")

        with col_b:
            st.markdown(f"### Ramos con mayor {CLAIMS_PREMIUM_RATIO_LABEL_ES.lower()}")

            line_lr = prepare_premium_claims_summary(filtered_df, ["line_of_business_standard"])
            line_lr = line_lr[line_lr["primas"] >= minimum_premium]
            line_lr = line_lr.sort_values("siniestralidad", ascending=False).head(15)
            line_lr["primas_mm"] = line_lr["primas"] / 1_000_000

            if not line_lr.empty:
                fig_line_high_lr = px.bar(
                    line_lr,
                    x="line_of_business_standard",
                    y="siniestralidad",
                    title=f"Top ramos por {CLAIMS_PREMIUM_RATIO_LABEL_ES.lower()}",
                    labels={
                        "line_of_business_standard": "Ramo",
                        "siniestralidad": CLAIMS_PREMIUM_RATIO_LABEL_ES
                    },
                    hover_data=["primas_mm"]
                )

                fig_line_high_lr.update_yaxes(tickformat=".1%")
                st.plotly_chart(fig_line_high_lr, width="stretch")
            else:
                st.info("No hay ramos que superen el umbral mínimo de primas seleccionado.")

        st.markdown("### Ramos con mayor crecimiento anual de primas")

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
                title=f"Top crecimiento de primas por ramo — {latest_year}",
                labels={
                    "line_of_business_standard": "Ramo",
                    "premium_growth": "Crecimiento"
                }
            )

            fig_line_growth.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_line_growth, width="stretch")
        else:
            st.info("No hay datos suficientes para mostrar crecimiento por ramo con el umbral seleccionado.")

        st.warning(
            "Nota: estas señales son automáticas y deben interpretarse considerando tamaño de cartera, "
            "cambios de clasificación, efectos extraordinarios y calidad de la información fuente."
        )
    except Exception as exc:
        render_section_error(exc)


# ============================================================
# TAB 6 — REINSURANCE VIEW
# ============================================================

if selected_view == "Reinsurance View":
    try:
        indicadores_df = load_indicadores_gestion_2025()
        indicadores_validation_df = load_indicadores_gestion_validation()
        indicadores_validation_flags_df = load_indicadores_gestion_validation_flags()
        pipeline_status = load_pipeline_status()

        st.subheader("Reinsurance View")
        st.caption(
            "Vista exploratoria basada en Fasecolda - Indicadores de Gestión 2025. "
            "Estos datos vienen de una fuente distinta a Ciudades y Ramos y deben validarse metodológicamente antes de usarse como dato final."
        )
        st.info(
            "Metodología: fuente Fasecolda - Indicadores de Gestión 2025. "
            "Estado: fuente complementaria exploratoria. "
            "Los ratios se recalculan a nivel agregado y no se suman. "
            "Los ramos agregados pueden duplicar ramos individuales y pueden excluirse de rankings. "
            "La fuente requiere revisión metodológica adicional antes de integrarse al modelo regional core."
        )

        if indicadores_df.empty:
            st.warning(
                "No se encontró la tabla fact_indicadores_gestion_2025. "
                "Ejecuta primero `python src\\load_indicadores_gestion_to_duckdb.py`."
            )
        else:
            exclude_aggregate_lines = st.checkbox(
                "Exclude aggregate lines from rankings",
                value=True,
                help=(
                    "Excluye ramos con lob_group = AGGREGATE en el mapping formal "
                    "y totales como TOTAL DAÑOS, TOTAL PERSONAS y TOTAL SEGURIDAD SOCIAL."
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
                            f"'{selected_company}' → '{mapped_company}'."
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
                            f"Ramo mapeado para Indicadores de Gestión: '{selected_line}' → '{mapped_line}'."
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
                st.warning(
                    "Data not available for the selected reinsurance filters. "
                    "Please adjust the company or line of business selection."
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
                st.dataframe(pd.DataFrame(benchmark_rows), width="stretch", hide_index=True)

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
                st.dataframe(
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
                st.dataframe(evo_display, width="stretch", hide_index=True)

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
                re_wide.groupby("line_of_business_standard", as_index=False)
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

            st.dataframe(
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
                    st.dataframe(validation_counts_re, width="stretch")

                with col_v2:
                    st.dataframe(indicadores_validation_df, width="stretch")

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

                st.dataframe(flag_counts, width="stretch")

            st.warning(
                "Metodología: esta vista usa Fasecolda - Indicadores de Gestión 2025. "
                "Los ratios se recalculan a nivel agregado y no se suman. "
                "Los ramos agregados pueden duplicar ramos individuales y deben tratarse con cautela. "
                "La fuente está en validación exploratoria antes de integrarse al core regional principal."
            )
    except Exception as exc:
        render_section_error(exc)


# ============================================================
# TAB 7 — DATA STATUS
# ============================================================

if selected_view == "Data Status":
    try:
        validation_df = load_validation_report()
        indicadores_df = load_indicadores_gestion_2025()
        indicadores_validation_df = load_indicadores_gestion_validation()
        indicadores_validation_flags_df = load_indicadores_gestion_validation_flags()
        pipeline_status = load_pipeline_status()

        render_section_header(
            "Data Governance Status",
            "Coverage, traceability, mapping readiness and validation warnings for the selected country module.",
        )

        st.info(
            "This Streamlit Cloud demo uses a static DuckDB snapshot included in the demo branch. "
            "Phase 3 adds a manual-run Fasecolda ingestion pipeline, but the app does not execute "
            "that pipeline automatically on launch. Scheduled automation is a future deployment step."
        )

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
            render_metric_card("Primary source", "Ciudades y Ramos", "Fasecolda public data")
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

        st.info(
            "Core market analytics use the latest available monthly cut for each year because "
            "Fasecolda - Ciudades y Ramos files are cumulative period cuts. The extracted VALOR "
            "field is treated as thousands of COP and converted to COP for KPIs, charts, briefs, "
            "exports and technical signals. Data Status tables below show all loaded source records "
            "for traceability."
        )

        st.warning(
            "Professional use note: figures are intended for internal market intelligence and broker "
            "meeting preparation. Validate figures against the source files before using them in formal "
            "client, market, actuarial, or financial presentations."
        )

        st.warning(
            "Methodology note: Claims / Premiums shown in the app is an analytical claims/premiums ratio. "
            "It should not be interpreted as Fasecolda's official technical loss ratio or combined "
            "ratio unless specifically stated. SOAT should be reviewed carefully because Fasecolda's "
            "technical views may include methodological components not captured by a simple "
            "claims/premiums ratio."
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
        source_summary["usage"] = "Primas, siniestros, ratio siniestros / primas, compañías, ramos, ciudades"

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

        st.dataframe(source_summary, width="stretch")

        st.info(
            "La fuente principal del core regional es Fasecolda - Ciudades y Ramos. "
            "Indicadores de Gestión 2025 se está usando como fuente complementaria exploratoria "
            "para la Reinsurance View y requiere validación metodológica antes de integrarse "
            "al core regional principal."
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
            "gross_written_premium": "Primas",
            "claims": "Siniestros",
            "reinsurance_ceded_premium": "Cesión al reaseguro",
            "technical_result": "Resultado técnico",
            "net_result": "Resultado neto",
            "taxes_or_contributions": "Impuestos / contribuciones"
        }

        available_metrics["metric_display"] = available_metrics["metric_name"].map(metric_name_display).fillna(available_metrics["metric_name"])

        st.dataframe(
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

        st.dataframe(files_summary, width="stretch")

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
                st.dataframe(validation_counts, width="stretch")

            with col_j:
                st.dataframe(validation_df, width="stretch")

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
                st.dataframe(indicadores_validation_counts, width="stretch")

            with col_l:
                st.dataframe(indicadores_validation_df, width="stretch")

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
            st.dataframe(indicadores_flags_status, width="stretch")

        st.info(
            "Current version: Colombia MVP Demo, Phase 3 - automated regulatory ingestion pipeline. "
            "This version is suitable for limited internal broker testing. It is not yet a corporate-hosted "
            "production service. The ingestion pipeline is manual-run only until a scheduling environment "
            "is approved."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 8 — REPORTS / EXPORT
# ============================================================

if selected_view == "Reports / Export":
    try:
        indicadores_df = load_indicadores_gestion_2025()

        render_section_header(
            "Export Center",
            "Copy-ready broker outputs and lightweight data exports for meetings, emails, notes and slide preparation.",
        )

        latest_available_year = max(selected_years) if selected_years else "N/A"
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
            st.dataframe(filtered_df.head(1000), width="stretch")
            csv_bytes = dataframe_to_csv_bytes(filtered_df)
            excel_bytes = dataframe_to_excel_bytes(filtered_df, sheet_name="filtered_data")
            data_col_a, data_col_b = st.columns(2)
            with data_col_a:
                st.download_button(
                    label="Download filtered data CSV",
                    data=csv_bytes,
                    file_name="market_filtered_data.csv",
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
                        file_name="market_filtered_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="reports_download_filtered_data_excel",
                    )
        else:
            selected_markdown = markdown_exports.get(export_type, "Data not available.")
            if export_type == "PPT-Ready Bullets":
                st.code(selected_markdown, language="markdown")
            else:
                st.markdown(selected_markdown)

            safe_scope = sanitize_export_filename(f"{selected_company}_{selected_line}_{export_type}")
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
            "Export methodology: Claims / Premiums is analytical and not necessarily official technical "
            "siniestralidad or combined ratio. Reinsurance indicators are exploratory. External intelligence "
            "is curated/manual and may be empty. Validate figures before formal client or market presentations."
        )
    except Exception as exc:
        render_section_error(exc)

# ============================================================
# TAB 9 — DATA TABLE
# ============================================================

if selected_view == "Data Table":
    try:
        st.subheader("Data Table")
        st.caption("Vista preliminar de los primeros 1,000 registros filtrados.")

        st.dataframe(
            filtered_df.head(1000),
            width="stretch"
        )

        st.markdown("### Descripción del dataset")

        st.write(
            """
            Este módulo utiliza información pública de Fasecolda sobre primas y siniestros.
            La información fue consolidada, limpiada y cargada en DuckDB bajo una estructura regional
            llamada `fact_market_core`.
        
            Colombia es el primer módulo operativo del LAC Insurance Market Intelligence Hub.
            La arquitectura se está preparando para incorporar otros países de Latinoamérica y el Caribe,
            incluso cuando no todos los países tengan el mismo nivel de detalle disponible.
            """
        )
    except Exception as exc:
        render_section_error(exc)
