from pathlib import Path
import unicodedata

import duckdb
import pandas as pd


DB_FILE = Path("data/database/insurance_market.duckdb")
OUTPUT_FILE = Path("outputs/indicadores_gestion_2025_validation_report.csv")
DETAIL_FILE = Path("outputs/indicadores_gestion_2025_validation_detail.csv")
FLAGS_FILE = Path("outputs/indicadores_gestion_2025_flags.csv")

TABLE_NAME = "fact_indicadores_gestion_2025"
LOB_MAPPING_TABLE = "dim_line_of_business_mapping"
TARGET_SOURCE = "FASECOLDA - INDICADORES DE GESTION"

EXPECTED_METRICS = [
    "gross_written_premium",
    "retained_premium",
    "reinsurance_ceded_premium",
    "retention_ratio",
    "reinsurance_cession_ratio",
    "paid_claims",
]


def normalize_match_text(value):
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def safe_ratio(numerator, denominator):
    denominator = denominator.mask(denominator == 0)
    return numerator / denominator


def read_mapping_table(conn):
    try:
        return conn.execute(f"""
            SELECT *
            FROM {LOB_MAPPING_TABLE}
        """).fetchdf()
    except Exception:
        return pd.DataFrame()


def build_aggregate_lookup(mapping_df):
    aggregate_names = {
        "TOTAL DANOS",
        "TOTAL DAÑOS",
        "TOTAL PERSONAS",
        "TOTAL SEGURIDAD SOCIAL",
    }

    if mapping_df.empty:
        return {normalize_match_text(value) for value in aggregate_names}

    required_cols = {
        "country",
        "source",
        "source_line_of_business",
        "standard_line_of_business",
        "lob_group",
    }

    if not required_cols.issubset(mapping_df.columns):
        return {normalize_match_text(value) for value in aggregate_names}

    mapping = mapping_df.copy()
    mapping["lob_group_norm"] = mapping["lob_group"].map(normalize_match_text)

    aggregate_mapping = mapping[mapping["lob_group_norm"] == "AGGREGATE"]

    for _, row in aggregate_mapping.iterrows():
        aggregate_names.add(row.get("source_line_of_business", ""))
        aggregate_names.add(row.get("standard_line_of_business", ""))

    return {normalize_match_text(value) for value in aggregate_names if str(value).strip()}


def attach_lob_group(wide, mapping_df):
    if mapping_df.empty or "lob_group" not in mapping_df.columns:
        wide["lob_group"] = pd.NA
        return wide

    mapping = mapping_df.copy()
    mapping["source_norm"] = mapping["source"].map(normalize_match_text)
    mapping["source_lob_norm"] = mapping["source_line_of_business"].map(normalize_match_text)
    mapping["standard_lob_norm"] = mapping["standard_line_of_business"].map(normalize_match_text)

    target_mapping = mapping[mapping["source_norm"] == normalize_match_text(TARGET_SOURCE)].copy()
    target_mapping = target_mapping.drop_duplicates("source_lob_norm")
    target_mapping = target_mapping[["source_lob_norm", "lob_group"]]

    wide["line_norm"] = wide["line_of_business_standard"].map(normalize_match_text)
    wide = wide.merge(
        target_mapping,
        left_on="line_norm",
        right_on="source_lob_norm",
        how="left",
    )
    wide = wide.drop(columns=["source_lob_norm"])
    return wide


def add_result(results, test_name, count, detail, warning_when_positive=True):
    if warning_when_positive:
        result = "PASS" if count == 0 else "WARNING"
    else:
        result = "INFO"
    results.append(
        {
            "test_name": test_name,
            "result": result,
            "detail": detail,
        }
    )


def build_flags(wide):
    flag_rows = []

    def add_flags(mask, flag_name, detail, severity="WARNING"):
        flagged = wide.loc[mask].copy()
        for _, row in flagged.iterrows():
            flag_rows.append(
                {
                    "flag_name": flag_name,
                    "severity": severity,
                    "country": row.get("country"),
                    "year": row.get("year"),
                    "company_standard": row.get("company_standard"),
                    "line_of_business_standard": row.get("line_of_business_standard"),
                    "source": row.get("source"),
                    "period_date": row.get("period_date"),
                    "source_file": row.get("source_file"),
                    "gross_written_premium": row.get("gross_written_premium"),
                    "retained_premium": row.get("retained_premium"),
                    "reinsurance_ceded_premium": row.get("reinsurance_ceded_premium"),
                    "retention_ratio": row.get("retention_ratio"),
                    "reinsurance_cession_ratio": row.get("reinsurance_cession_ratio"),
                    "paid_claims": row.get("paid_claims"),
                    "calculated_retention_ratio": row.get("calculated_retention_ratio"),
                    "calculated_cession_ratio": row.get("calculated_cession_ratio"),
                    "calculated_paid_claims_ratio": row.get("calculated_paid_claims_ratio"),
                    "detail": detail,
                }
            )

    add_flags(
        wide["gross_written_premium"].notna() & (wide["gross_written_premium"] <= 0),
        "gross_written_premium_non_positive",
        "gross_written_premium is less than or equal to zero.",
    )
    add_flags(
        wide["retained_premium"].notna()
        & wide["gross_written_premium"].notna()
        & (wide["retained_premium"] > wide["gross_written_premium"]),
        "retained_premium_gt_gross_written_premium",
        "retained_premium is greater than gross_written_premium.",
    )
    add_flags(
        wide["reinsurance_ceded_premium"].notna()
        & (wide["reinsurance_ceded_premium"] < 0),
        "reinsurance_ceded_premium_negative",
        "reinsurance_ceded_premium is negative.",
    )
    add_flags(
        wide["retention_ratio"].notna()
        & ((wide["retention_ratio"] < 0) | (wide["retention_ratio"] > 1.2)),
        "retention_ratio_outside_0_1_2",
        "retention_ratio is outside the expected 0 to 1.2 range.",
    )
    add_flags(
        wide["reinsurance_cession_ratio"].notna()
        & ((wide["reinsurance_cession_ratio"] < -0.2) | (wide["reinsurance_cession_ratio"] > 1.2)),
        "cession_ratio_outside_minus_0_2_1_2",
        "reinsurance_cession_ratio is outside the expected -0.2 to 1.2 range.",
    )
    add_flags(
        wide["calculated_paid_claims_ratio"].notna()
        & (wide["calculated_paid_claims_ratio"] > 1.0),
        "paid_claims_ratio_above_1",
        "paid_claims divided by gross_written_premium is above 1.0.",
    )
    add_flags(
        wide["is_aggregate_line"],
        "aggregate_line",
        "Line of business is an aggregate total and may duplicate individual lines.",
        severity="INFO",
    )
    add_flags(
        wide["possible_duplicated_aggregate_impact"],
        "possible_duplicated_aggregate_impact",
        "Aggregate line coexists with individual lines for the same company/year.",
    )
    add_flags(
        wide["retention_ratio_difference"].notna()
        & (wide["retention_ratio_difference"].abs() > 0.01),
        "retention_ratio_material_difference",
        "Extracted retention_ratio differs from calculated retained_premium / gross_written_premium by more than 1 percentage point.",
    )
    add_flags(
        wide["cession_ratio_difference"].notna()
        & (wide["cession_ratio_difference"].abs() > 0.01),
        "cession_ratio_material_difference",
        "Extracted reinsurance_cession_ratio differs from calculated ceded premium / gross_written_premium by more than 1 percentage point.",
    )

    return pd.DataFrame(flag_rows)


def main():
    print("Connecting to DuckDB...")

    conn = duckdb.connect(str(DB_FILE))

    df = conn.execute(f"""
        SELECT *
        FROM {TABLE_NAME}
    """).fetchdf()
    mapping_df = read_mapping_table(conn)

    conn.close()

    print("Dataset loaded:")
    print(df.shape)

    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")

    group_cols = [
        "country",
        "year",
        "company_standard",
        "line_of_business_standard",
    ]

    wide = (
        df.pivot_table(
            index=group_cols,
            columns="metric_name",
            values="metric_value",
            aggfunc="sum",
        )
        .reset_index()
    )
    wide.columns.name = None

    meta = (
        df.groupby(group_cols, as_index=False)
        .agg(
            source=("source", "first"),
            period_date=("period_date", "max"),
            source_file=("source_file", lambda values: "; ".join(sorted(set(values.dropna().astype(str))))),
        )
    )
    wide = wide.merge(meta, on=group_cols, how="left")

    for col in EXPECTED_METRICS:
        if col not in wide.columns:
            wide[col] = pd.NA
        wide[col] = pd.to_numeric(wide[col], errors="coerce")

    wide["calculated_ceded_premium"] = (
        wide["gross_written_premium"] - wide["retained_premium"]
    )
    wide["calculated_retention_ratio"] = safe_ratio(
        wide["retained_premium"],
        wide["gross_written_premium"],
    )
    wide["calculated_cession_ratio"] = safe_ratio(
        wide["reinsurance_ceded_premium"],
        wide["gross_written_premium"],
    )
    wide["calculated_paid_claims_ratio"] = safe_ratio(
        wide["paid_claims"],
        wide["gross_written_premium"],
    )

    wide["ceded_difference"] = (
        wide["reinsurance_ceded_premium"] - wide["calculated_ceded_premium"]
    )
    wide["retention_ratio_difference"] = (
        wide["retention_ratio"] - wide["calculated_retention_ratio"]
    )
    wide["cession_ratio_difference"] = (
        wide["reinsurance_cession_ratio"] - wide["calculated_cession_ratio"]
    )

    wide = attach_lob_group(wide, mapping_df)
    aggregate_lookup = build_aggregate_lookup(mapping_df)
    wide["is_aggregate_line"] = wide["line_of_business_standard"].map(
        lambda value: normalize_match_text(value) in aggregate_lookup
    )

    company_year = (
        wide.groupby(["country", "year", "company_standard"], as_index=False)
        .agg(
            aggregate_lines=("is_aggregate_line", "sum"),
            total_lines=("line_of_business_standard", "nunique"),
        )
    )
    company_year["individual_lines"] = (
        company_year["total_lines"] - company_year["aggregate_lines"]
    )
    company_year["has_duplicate_aggregate_context"] = (
        (company_year["aggregate_lines"] > 0) & (company_year["individual_lines"] > 0)
    )

    wide = wide.merge(
        company_year[
            [
                "country",
                "year",
                "company_standard",
                "has_duplicate_aggregate_context",
            ]
        ],
        on=["country", "year", "company_standard"],
        how="left",
    )
    wide["possible_duplicated_aggregate_impact"] = (
        wide["is_aggregate_line"] & wide["has_duplicate_aggregate_context"].fillna(False)
    )

    flags_df = build_flags(wide)

    validation_results = []

    add_result(
        validation_results,
        "total_rows_long_format",
        len(df),
        f"{len(df):,} records in long format",
        warning_when_positive=False,
    )
    add_result(
        validation_results,
        "total_rows_wide_format",
        len(wide),
        f"{len(wide):,} company/line combinations",
        warning_when_positive=False,
    )
    add_result(
        validation_results,
        "available_companies",
        wide["company_standard"].nunique(),
        f"{wide['company_standard'].nunique():,} unique companies",
        warning_when_positive=False,
    )
    add_result(
        validation_results,
        "available_lines",
        wide["line_of_business_standard"].nunique(),
        f"{wide['line_of_business_standard'].nunique():,} unique lines of business",
        warning_when_positive=False,
    )
    add_result(
        validation_results,
        "available_sources",
        df["source"].nunique(),
        f"{df['source'].nunique():,} source names",
        warning_when_positive=False,
    )

    for col in EXPECTED_METRICS:
        null_count = int(wide[col].isna().sum())
        add_result(
            validation_results,
            f"null_values_{col}",
            null_count,
            f"{null_count:,} null values",
        )

    flag_specs = [
        ("gross_written_premium_non_positive", "gross_written_premium_non_positive"),
        ("retained_premium_greater_than_written_premium", "retained_premium_gt_gross_written_premium"),
        ("negative_reinsurance_ceded_premium", "reinsurance_ceded_premium_negative"),
        ("retention_ratio_out_of_expected_range", "retention_ratio_outside_0_1_2"),
        ("cession_ratio_out_of_expected_range", "cession_ratio_outside_minus_0_2_1_2"),
        ("paid_claims_ratio_above_1", "paid_claims_ratio_above_1"),
        ("aggregate_lines", "aggregate_line"),
        ("possible_duplicated_aggregate_impact", "possible_duplicated_aggregate_impact"),
        ("retention_ratio_reconciliation_difference", "retention_ratio_material_difference"),
        ("cession_ratio_reconciliation_difference", "cession_ratio_material_difference"),
    ]

    for test_name, flag_name in flag_specs:
        count = int((flags_df["flag_name"] == flag_name).sum()) if not flags_df.empty else 0
        add_result(
            validation_results,
            test_name,
            count,
            f"{count:,} flagged records",
        )

    material_ceded_diff = int(
        (
            wide["ceded_difference"].notna()
            & (wide["ceded_difference"].abs() > 1_000)
        ).sum()
    )
    add_result(
        validation_results,
        "ceded_premium_reconciliation_difference",
        material_ceded_diff,
        f"{material_ceded_diff:,} records with material difference between reported and calculated ceded premium",
    )

    total_flags = len(flags_df)
    add_result(
        validation_results,
        "total_validation_flags",
        total_flags,
        f"{total_flags:,} total validation flags written to {FLAGS_FILE}",
        warning_when_positive=False,
    )

    validation_df = pd.DataFrame(validation_results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    validation_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    wide.to_csv(DETAIL_FILE, index=False, encoding="utf-8-sig")
    flags_df.to_csv(FLAGS_FILE, index=False, encoding="utf-8-sig")

    print("\nValidation report saved to:")
    print(OUTPUT_FILE)
    print("\nValidation detail saved to:")
    print(DETAIL_FILE)
    print("\nValidation flags saved to:")
    print(FLAGS_FILE)

    print("\nValidation results:")
    print(validation_df)
    print("\nFlag counts:")
    if flags_df.empty:
        print("No flags generated.")
    else:
        print(
            flags_df
            .groupby(["severity", "flag_name"], as_index=False)
            .size()
            .rename(columns={"size": "records"})
            .sort_values(["severity", "records"], ascending=[True, False])
        )

    print("\nIndicadores de Gestion 2025 validation completed.")


if __name__ == "__main__":
    main()
