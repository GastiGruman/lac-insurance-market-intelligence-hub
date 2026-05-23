from datetime import datetime
from pathlib import Path
import unicodedata

import pandas as pd

from .config import PipelineConfig, ensure_pipeline_dirs
from .pipeline_logger import append_event


SOURCE_NAME = "FASECOLDA - CIUDADES Y RAMOS"


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().split())


def read_csv_flexible(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {normalize_text(col): col for col in columns}
    for candidate in candidates:
        found = normalized.get(normalize_text(candidate))
        if found:
            return found
    return None


def _load_mappings(config: PipelineConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    company_mapping = read_csv_flexible(config.company_mapping_path) if config.company_mapping_path.exists() else pd.DataFrame()
    lob_mapping = read_csv_flexible(config.lob_mapping_path) if config.lob_mapping_path.exists() else pd.DataFrame()
    return company_mapping, lob_mapping


def _apply_mappings(df: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    company_mapping, lob_mapping = _load_mappings(config)
    df["company_name_norm"] = df["company_name"].map(normalize_text)
    df["line_of_business_norm"] = df["line_of_business"].map(normalize_text)

    if not company_mapping.empty:
        company_mapping = company_mapping[company_mapping["source"].map(normalize_text) == normalize_text(SOURCE_NAME)].copy()
        company_mapping["source_company_norm"] = company_mapping["source_company"].map(normalize_text)
        company_mapping = company_mapping.drop_duplicates("source_company_norm")
        df = df.merge(
            company_mapping[["source_company_norm", "standard_company"]],
            left_on="company_name_norm",
            right_on="source_company_norm",
            how="left",
        )
        df = df.drop(columns=["source_company_norm"])
    else:
        df["standard_company"] = pd.NA

    if not lob_mapping.empty:
        lob_mapping = lob_mapping[lob_mapping["source"].map(normalize_text) == normalize_text(SOURCE_NAME)].copy()
        lob_mapping["source_line_of_business_norm"] = lob_mapping["source_line_of_business"].map(normalize_text)
        lob_mapping = lob_mapping.drop_duplicates("source_line_of_business_norm")
        df = df.merge(
            lob_mapping[["source_line_of_business_norm", "standard_line_of_business", "lob_group"]],
            left_on="line_of_business_norm",
            right_on="source_line_of_business_norm",
            how="left",
        )
        df = df.drop(columns=["source_line_of_business_norm"])
    else:
        df["standard_line_of_business"] = pd.NA
        df["lob_group"] = pd.NA

    df["company_name_standard"] = df["standard_company"].fillna(df["company_name_norm"])
    df["line_of_business_standard"] = df["standard_line_of_business"].fillna(df["line_of_business_norm"])
    df["lob_group"] = df["lob_group"].fillna("UNMAPPED")

    unmapped_companies = (
        df[df["standard_company"].isna()][["country", "source", "company_name", "company_name_norm"]]
        .drop_duplicates()
        .sort_values("company_name_norm")
    )
    unmapped_lines = (
        df[df["standard_line_of_business"].isna()][["country", "source", "line_of_business", "line_of_business_norm"]]
        .drop_duplicates()
        .sort_values("line_of_business_norm")
    )
    unmapped_companies.to_csv(config.metadata_dir / "unmapped_companies.csv", index=False, encoding="utf-8-sig")
    unmapped_lines.to_csv(config.metadata_dir / "unmapped_lines_of_business.csv", index=False, encoding="utf-8-sig")
    return df.drop(columns=["standard_company", "standard_line_of_business"], errors="ignore")


def _read_one_workbook(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Base")
    company_col = _find_column(raw.columns.tolist(), ["COMPAÑÍA", "COMPAÑIA", "COMPANIA"])
    type_col = _find_column(raw.columns.tolist(), ["Primas/Siniestros", "PRIMAS/Siniestros", "PRIMAS SINIESTROS"])
    line_col = _find_column(raw.columns.tolist(), ["RAMOS", "RAMO"])
    city_col = _find_column(raw.columns.tolist(), ["CIUDAD", "DEPARTAMENTO"])
    value_col = _find_column(raw.columns.tolist(), ["VALOR"])
    date_col = _find_column(raw.columns.tolist(), ["FECHA"])
    required = [company_col, type_col, line_col, city_col, value_col, date_col]
    if any(col is None for col in required):
        raise ValueError(f"Missing expected Ciudades y Ramos columns in {path.name}")

    df = raw[[company_col, type_col, line_col, city_col, value_col, date_col]].copy()
    df.columns = ["company_name", "value_type", "line_of_business", "city", "value", "period_date"]
    df["source_file"] = path.name
    df["source_sheet"] = "Base"
    return df


def process_ciudades_ramos(config: PipelineConfig) -> pd.DataFrame:
    ensure_pipeline_dirs(config)
    files = sorted(
        set(config.raw_dir.glob("**/*Ciudades*y*Ramos*.xls*"))
        | set(config.raw_dir.glob("**/*ciudades*y*ramos*.xls*"))
        | set(config.raw_dir.glob("**/*Primas*y*siniestros*.xls*"))
        | set(config.raw_dir.glob("**/*primas*y*siniestros*.xls*"))
    )

    frames: list[pd.DataFrame] = []
    errors: list[dict] = []
    for path in files:
        try:
            frames.append(_read_one_workbook(path))
        except Exception as exc:
            errors.append({"source_file": str(path), "error_message": str(exc)})

    if not frames:
        append_event(config, "process_ciudades_ramos", "WARNING", "No local Ciudades y Ramos raw files were available.")
        empty = pd.DataFrame()
        empty.to_csv(config.processed_dir / "ciudades_ramos_normalized.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(errors).to_csv(config.metadata_dir / "ciudades_ramos_processing_errors.csv", index=False, encoding="utf-8-sig")
        return empty

    df = pd.concat(frames, ignore_index=True)
    df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
    df["year"] = df["period_date"].dt.year
    df["month"] = df["period_date"].dt.month
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["company_name"] = df["company_name"].astype(str).str.strip()
    df["line_of_business"] = df["line_of_business"].astype(str).str.strip()
    df["source_file"] = df["source_file"].astype(str).str.strip()
    company_key = df["company_name"].map(normalize_text)
    line_key = df["line_of_business"].map(normalize_text)
    missing_text_values = {"", "NAN", "NONE", "NULL", "<NA>"}

    valid_mask = (
        df["period_date"].notna()
        & df["year"].between(2010, datetime.now().year + 1)
        & df["month"].between(1, 12)
        & df["value"].notna()
        & ~company_key.isin(missing_text_values)
        & ~line_key.isin(missing_text_values)
        & df["source_file"].ne("")
    )
    rejected = df.loc[~valid_mask].copy()
    rejected.to_csv(config.metadata_dir / "ciudades_ramos_rejected_rows.csv", index=False, encoding="utf-8-sig")
    df = df.loc[valid_mask].copy()
    df["country"] = config.country
    df["source"] = SOURCE_NAME
    df["update_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df["value_type_norm"] = df["value_type"].map(normalize_text)
    df["gross_written_premium"] = df["value"].where(df["value_type_norm"].eq("PRIMAS"))
    df["claims"] = df["value"].where(df["value_type_norm"].eq("SINIESTROS"))
    df["loss_ratio"] = pd.NA
    df["retained_premium"] = pd.NA
    df["reinsurance_ceded_premium"] = pd.NA
    df["reinsurance_cession_ratio"] = pd.NA
    df["retention_ratio"] = pd.NA
    df["paid_claims"] = pd.NA
    df["department"] = pd.NA

    df = _apply_mappings(df, config)
    output_columns = [
        "country", "source", "year", "month", "period_date", "company_name",
        "company_name_norm", "company_name_standard", "line_of_business",
        "line_of_business_norm", "line_of_business_standard", "lob_group", "city",
        "department", "gross_written_premium", "claims", "loss_ratio",
        "retained_premium", "reinsurance_ceded_premium", "reinsurance_cession_ratio",
        "retention_ratio", "paid_claims", "source_file", "source_sheet", "update_date",
    ]
    df = df[output_columns]
    df.to_csv(config.processed_dir / "ciudades_ramos_normalized.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(errors).to_csv(config.metadata_dir / "ciudades_ramos_processing_errors.csv", index=False, encoding="utf-8-sig")
    append_event(config, "process_ciudades_ramos", "PASS", f"Processed {len(df):,} Ciudades y Ramos rows.")
    return df
