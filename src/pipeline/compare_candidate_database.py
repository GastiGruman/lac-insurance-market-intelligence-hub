from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from .config import get_config


REQUIRED_APP_TABLES = [
    "fact_market_core",
    "fact_fasecolda_market",
    "fact_indicadores_gestion_2025",
    "dim_company_mapping",
    "dim_line_of_business_mapping",
]

REQUIRED_MARKET_CORE_COLUMNS = [
    "country",
    "source",
    "period_date",
    "year",
    "month",
    "company_standard",
    "line_of_business_standard",
    "metric_name",
    "metric_value",
    "source_file",
]

COMPARISON_TOLERANCE = 0.01


@dataclass(frozen=True)
class DatabaseTarget:
    label: str
    path: Path


def _connect(target: DatabaseTarget) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(target.path), read_only=True)


def _tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    return sorted(row[0] for row in conn.execute("SHOW TABLES").fetchall())


def _describe(conn: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    df = conn.execute(f"DESCRIBE {table}").fetchdf()
    df["table_name"] = table
    return df


def _has_column(conn: duckdb.DuckDBPyConnection, table: str, column: str) -> bool:
    return column in set(_describe(conn, table)["column_name"].tolist())


def _table_summary(target: DatabaseTarget) -> pd.DataFrame:
    rows = []
    with _connect(target) as conn:
        for table in _tables(conn):
            row = {"database": target.label, "table_name": table}
            row["row_count"] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if _has_column(conn, table, "year"):
                year_min, year_max = conn.execute(
                    f"SELECT MIN(year), MAX(year) FROM {table}"
                ).fetchone()
                row["min_year"] = year_min
                row["max_year"] = year_max
            else:
                row["min_year"] = pd.NA
                row["max_year"] = pd.NA
            if _has_column(conn, table, "period_date"):
                date_min, date_max = conn.execute(
                    f"SELECT MIN(period_date), MAX(period_date) FROM {table}"
                ).fetchone()
                row["min_period_date"] = date_min
                row["max_period_date"] = date_max
            else:
                row["min_period_date"] = pd.NA
                row["max_period_date"] = pd.NA
            rows.append(row)
    return pd.DataFrame(rows)


def _schema_comparison(current: DatabaseTarget, candidate: DatabaseTarget) -> pd.DataFrame:
    frames = []
    for target in [current, candidate]:
        with _connect(target) as conn:
            for table in _tables(conn):
                schema = _describe(conn, table)
                schema["database"] = target.label
                frames.append(schema[["database", "table_name", "column_name", "column_type", "null"]])
    schema_all = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if schema_all.empty:
        return schema_all

    current_schema = schema_all[schema_all["database"] == current.label].rename(
        columns={"column_type": "current_type", "null": "current_null"}
    )
    candidate_schema = schema_all[schema_all["database"] == candidate.label].rename(
        columns={"column_type": "candidate_type", "null": "candidate_null"}
    )
    comparison = current_schema.merge(
        candidate_schema,
        on=["table_name", "column_name"],
        how="outer",
        suffixes=("_current", "_candidate"),
    )
    comparison["status"] = "MATCH"
    comparison.loc[comparison["database_current"].isna(), "status"] = "CANDIDATE_ONLY"
    comparison.loc[comparison["database_candidate"].isna(), "status"] = "CURRENT_ONLY"
    type_mismatch = (
        comparison["current_type"].notna()
        & comparison["candidate_type"].notna()
        & (comparison["current_type"] != comparison["candidate_type"])
    )
    comparison.loc[type_mismatch, "status"] = "TYPE_MISMATCH"
    return comparison[
        [
            "table_name",
            "column_name",
            "current_type",
            "candidate_type",
            "current_null",
            "candidate_null",
            "status",
        ]
    ].sort_values(["table_name", "column_name"])


def _market_query(group_cols: list[str], where_clause: str = "TRUE") -> str:
    cols = ", ".join(group_cols)
    group_by = f"GROUP BY {cols}" if group_cols else ""
    select_cols = f"{cols}," if group_cols else ""
    return f"""
        SELECT
            {select_cols}
            SUM(CASE WHEN metric_name = 'gross_written_premium' THEN metric_value ELSE 0 END) AS gross_written_premium,
            SUM(CASE WHEN metric_name = 'claims' THEN metric_value ELSE 0 END) AS claims,
            COUNT(*) AS record_count
        FROM fact_market_core
        WHERE {where_clause}
        {group_by}
    """


def _market_summary(target: DatabaseTarget, group_cols: list[str], where_clause: str = "TRUE") -> pd.DataFrame:
    with _connect(target) as conn:
        df = conn.execute(_market_query(group_cols, where_clause)).fetchdf()
    if df.empty:
        return df
    df["claims_premiums_ratio"] = df["claims"] / df["gross_written_premium"].replace({0: pd.NA})
    df["database"] = target.label
    return df


def _merge_metric_frames(
    current_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    keys: list[str],
    metrics: list[str],
) -> pd.DataFrame:
    merged = current_df.merge(
        candidate_df,
        on=keys,
        how="outer",
        suffixes=("_current", "_candidate"),
    )
    for metric in metrics:
        current_col = f"{metric}_current"
        candidate_col = f"{metric}_candidate"
        if current_col in merged.columns and candidate_col in merged.columns:
            merged[f"{metric}_diff"] = merged[candidate_col] - merged[current_col]
            merged[f"{metric}_diff_pct"] = merged[f"{metric}_diff"] / merged[current_col].replace({0: pd.NA})
    return merged


def _yearly_totals(current: DatabaseTarget, candidate: DatabaseTarget) -> pd.DataFrame:
    current_df = _market_summary(current, ["year"]).drop(columns=["database"], errors="ignore")
    candidate_df = _market_summary(candidate, ["year"]).drop(columns=["database"], errors="ignore")
    return _merge_metric_frames(
        current_df,
        candidate_df,
        ["year"],
        ["gross_written_premium", "claims", "claims_premiums_ratio", "record_count"],
    ).sort_values("year")


def _source_comparison(current: DatabaseTarget, candidate: DatabaseTarget) -> pd.DataFrame:
    current_df = _market_summary(current, ["source"]).drop(columns=["database"], errors="ignore")
    candidate_df = _market_summary(candidate, ["source"]).drop(columns=["database"], errors="ignore")
    return _merge_metric_frames(
        current_df,
        candidate_df,
        ["source"],
        ["gross_written_premium", "claims", "claims_premiums_ratio", "record_count"],
    ).sort_values("source")


def _top_comparison(current: DatabaseTarget, candidate: DatabaseTarget, group_col: str) -> pd.DataFrame:
    current_df = _market_summary(current, [group_col]).drop(columns=["database"], errors="ignore")
    candidate_df = _market_summary(candidate, [group_col]).drop(columns=["database"], errors="ignore")
    all_df = pd.concat([current_df.assign(source_db="current"), candidate_df.assign(source_db="candidate")])
    top_keys = (
        all_df.groupby(group_col, as_index=False)["gross_written_premium"]
        .max()
        .sort_values("gross_written_premium", ascending=False)
        .head(20)[group_col]
        .tolist()
    )
    return _merge_metric_frames(
        current_df[current_df[group_col].isin(top_keys)],
        candidate_df[candidate_df[group_col].isin(top_keys)],
        [group_col],
        ["gross_written_premium", "claims", "claims_premiums_ratio", "record_count"],
    ).sort_values("gross_written_premium_candidate", ascending=False)


def _slice_comparison(current: DatabaseTarget, candidate: DatabaseTarget, name: str, where_clause: str) -> pd.DataFrame:
    current_df = _market_summary(current, ["year"], where_clause).drop(columns=["database"], errors="ignore")
    candidate_df = _market_summary(candidate, ["year"], where_clause).drop(columns=["database"], errors="ignore")
    comparison = _merge_metric_frames(
        current_df,
        candidate_df,
        ["year"],
        ["gross_written_premium", "claims", "claims_premiums_ratio", "record_count"],
    )
    comparison.insert(0, "review_slice", name)
    return comparison.sort_values("year")


def _reinsurance_comparison(current: DatabaseTarget, candidate: DatabaseTarget) -> pd.DataFrame:
    query = """
        SELECT
            year,
            metric_name,
            COUNT(*) AS record_count,
            SUM(metric_value) AS metric_value
        FROM fact_indicadores_gestion_2025
        GROUP BY year, metric_name
    """
    with _connect(current) as conn:
        current_df = conn.execute(query).fetchdf()
    with _connect(candidate) as conn:
        candidate_df = conn.execute(query).fetchdf()
    return _merge_metric_frames(
        current_df,
        candidate_df,
        ["year", "metric_name"],
        ["metric_value", "record_count"],
    ).sort_values(["year", "metric_name"])


def _critical_checks(
    current: DatabaseTarget,
    candidate: DatabaseTarget,
    table_summary: pd.DataFrame,
    schema_comparison: pd.DataFrame,
    yearly_totals: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    checks = []

    def add(name: str, result: str, detail: str) -> None:
        checks.append({"check_name": name, "result": result, "detail": detail})

    add(
        "candidate_exists",
        "PASS" if candidate.path.exists() else "ERROR",
        str(candidate.path),
    )

    if candidate.path.exists():
        try:
            with _connect(candidate) as conn:
                candidate_tables = set(_tables(conn))
            missing_tables = sorted(set(REQUIRED_APP_TABLES) - candidate_tables)
            add(
                "required_app_tables",
                "PASS" if not missing_tables else "ERROR",
                "All required app tables exist." if not missing_tables else f"Missing tables: {missing_tables}",
            )

            with _connect(candidate) as conn:
                candidate_columns = set(_describe(conn, "fact_market_core")["column_name"].tolist())
            missing_columns = sorted(set(REQUIRED_MARKET_CORE_COLUMNS) - candidate_columns)
            add(
                "required_fact_market_core_columns",
                "PASS" if not missing_columns else "ERROR",
                "All required fact_market_core columns exist." if not missing_columns else f"Missing columns: {missing_columns}",
            )
        except Exception as exc:
            add("candidate_open", "ERROR", str(exc))

    type_or_missing = schema_comparison[
        schema_comparison["table_name"].isin(REQUIRED_APP_TABLES)
        & schema_comparison["status"].isin(["CURRENT_ONLY", "TYPE_MISMATCH"])
    ]
    add(
        "app_schema_compatibility",
        "PASS" if type_or_missing.empty else "ERROR",
        "Required app table schema is compatible." if type_or_missing.empty else f"Schema issues: {len(type_or_missing)}",
    )

    current_core = table_summary[
        (table_summary["database"] == current.label) & (table_summary["table_name"] == "fact_market_core")
    ]
    candidate_core = table_summary[
        (table_summary["database"] == candidate.label) & (table_summary["table_name"] == "fact_market_core")
    ]
    if not current_core.empty and not candidate_core.empty:
        current_rows = int(current_core.iloc[0]["row_count"])
        candidate_rows = int(candidate_core.iloc[0]["row_count"])
        row_diff_pct = (candidate_rows - current_rows) / current_rows if current_rows else 0
        add(
            "fact_market_core_row_count",
            "PASS" if row_diff_pct >= -COMPARISON_TOLERANCE else "ERROR",
            f"Current rows: {current_rows:,}; candidate rows: {candidate_rows:,}; diff pct: {row_diff_pct:.4%}",
        )
        add(
            "year_range",
            "PASS"
            if (
                current_core.iloc[0]["min_year"] == candidate_core.iloc[0]["min_year"]
                and current_core.iloc[0]["max_year"] == candidate_core.iloc[0]["max_year"]
            )
            else "ERROR",
            f"Current: {current_core.iloc[0]['min_year']}-{current_core.iloc[0]['max_year']}; "
            f"candidate: {candidate_core.iloc[0]['min_year']}-{candidate_core.iloc[0]['max_year']}",
        )

    material_year_diff = pd.DataFrame()
    for metric in ["gross_written_premium", "claims"]:
        col = f"{metric}_diff_pct"
        if col in yearly_totals.columns:
            material_year_diff = pd.concat(
                [material_year_diff, yearly_totals[yearly_totals[col].abs() > COMPARISON_TOLERANCE]]
            )
    add(
        "yearly_premium_claims_reconciliation",
        "PASS" if material_year_diff.empty else "ERROR",
        "Yearly premium and claims totals are within tolerance."
        if material_year_diff.empty
        else f"Material yearly differences above {COMPARISON_TOLERANCE:.1%}: {len(material_year_diff)} rows",
    )

    result_df = pd.DataFrame(checks)
    if (result_df["result"] == "ERROR").any():
        recommendation = "Do not promote yet"
    elif (result_df["result"] == "WARNING").any():
        recommendation = "Promote after specific fixes"
    else:
        recommendation = "Promote now"
    return result_df, recommendation


def _write_summary(
    output_dir: Path,
    doc_path: Path,
    checks: pd.DataFrame,
    recommendation: str,
    table_summary: pd.DataFrame,
    schema_comparison: pd.DataFrame,
    yearly_totals: pd.DataFrame,
) -> None:
    current_core = table_summary[
        (table_summary["database"] == "current") & (table_summary["table_name"] == "fact_market_core")
    ]
    candidate_core = table_summary[
        (table_summary["database"] == "candidate") & (table_summary["table_name"] == "fact_market_core")
    ]
    extra_candidate_tables = sorted(
        set(table_summary[table_summary["database"] == "candidate"]["table_name"])
        - set(table_summary[table_summary["database"] == "current"]["table_name"])
    )
    max_premium_diff = yearly_totals.get("gross_written_premium_diff_pct", pd.Series(dtype="float64")).abs().max()
    max_claims_diff = yearly_totals.get("claims_diff_pct", pd.Series(dtype="float64")).abs().max()

    def markdown_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "No records.\n"
        columns = df.columns.tolist()
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join(["---"] * len(columns)) + " |",
        ]
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
        return "\n".join(lines)

    summary_lines = [
        "# Candidate Database Review",
        "",
        f"- Review date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- Current DB path: `data/database/insurance_market.duckdb`",
        "- Candidate DB path: `data/database/insurance_market_candidate.duckdb`",
        "- Pipeline mode used for candidate: `update-db`",
        f"- Promotion recommendation: **{recommendation}**",
        "",
        "## Critical Checks",
        "",
        markdown_table(checks),
        "",
        "## Main Differences",
        "",
        f"- Extra candidate tables: {', '.join(extra_candidate_tables) if extra_candidate_tables else 'None'}",
        f"- Current fact_market_core rows: {int(current_core.iloc[0]['row_count']):,}" if not current_core.empty else "- Current fact_market_core rows: N/A",
        f"- Candidate fact_market_core rows: {int(candidate_core.iloc[0]['row_count']):,}" if not candidate_core.empty else "- Candidate fact_market_core rows: N/A",
        f"- Max yearly premium difference pct: {max_premium_diff:.6%}" if pd.notna(max_premium_diff) else "- Max yearly premium difference pct: N/A",
        f"- Max yearly claims difference pct: {max_claims_diff:.6%}" if pd.notna(max_claims_diff) else "- Max yearly claims difference pct: N/A",
        "",
        "## Interpretation",
        "",
        "The candidate database is compared against the current stable demo database before any promotion. "
        "This candidate is app-compatible if all critical checks pass. However, if it only copies the current "
        "app tables and adds pipeline audit tables, promotion is operationally unnecessary until the pipeline "
        "is ready to rebuild or refresh the app-facing tables.",
        "",
        "## Required Next Actions",
        "",
        "- Review generated reconciliation files under `data/metadata/db_comparison/` locally.",
        "- Test the app against the candidate with `USE_CANDIDATE_DB=true` before any promotion.",
        "- Promote only after explicit approval and only if the recommendation is `Promote now`.",
    ]
    text = "\n".join(summary_lines) + "\n"
    (output_dir / "db_comparison_summary.md").write_text(text, encoding="utf-8")
    doc_path.write_text(text, encoding="utf-8")


def compare_databases() -> dict:
    config = get_config()
    output_dir = config.metadata_dir / "db_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_path = config.project_root / "docs" / "candidate_database_review.md"

    current = DatabaseTarget("current", config.current_db_path)
    candidate = DatabaseTarget("candidate", config.candidate_db_path)

    if not current.path.exists():
        raise FileNotFoundError(f"Current database not found: {current.path}")
    if not candidate.path.exists():
        raise FileNotFoundError(f"Candidate database not found: {candidate.path}")

    table_summary = pd.concat([_table_summary(current), _table_summary(candidate)], ignore_index=True)
    schema_comparison = _schema_comparison(current, candidate)
    yearly_totals = _yearly_totals(current, candidate)
    source_comparison = _source_comparison(current, candidate)
    company_top20 = _top_comparison(current, candidate, "company_standard")
    lob_top20 = _top_comparison(current, candidate, "line_of_business_standard")
    soat = _slice_comparison(current, candidate, "SOAT", "line_of_business_standard = 'SOAT'")
    bolivar = _slice_comparison(current, candidate, "BOLIVAR", "company_standard = 'BOLIVAR'")
    bolivar_fire = _slice_comparison(
        current,
        candidate,
        "BOLIVAR + INCENDIO Y LUCRO CESANTE",
        "company_standard = 'BOLIVAR' AND line_of_business_standard IN ('INCENDIO Y LUCRO CESANTE', 'INCENDIO Y LUCRO')",
    )
    reinsurance = _reinsurance_comparison(current, candidate)

    checks, recommendation = _critical_checks(current, candidate, table_summary, schema_comparison, yearly_totals)
    extra_candidate_tables = sorted(
        set(table_summary[table_summary["database"] == "candidate"]["table_name"])
        - set(table_summary[table_summary["database"] == "current"]["table_name"])
    )
    unchanged_check_columns = ["gross_written_premium_diff", "claims_diff", "record_count_diff"]
    unchanged_values = yearly_totals[unchanged_check_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    app_tables_unchanged = float(unchanged_values.abs().sum().sum()) < 1
    if recommendation == "Promote now" and extra_candidate_tables and app_tables_unchanged:
        recommendation = "Do not promote yet"
        checks = pd.concat(
            [
                checks,
                pd.DataFrame(
                    [
                        {
                            "check_name": "promotion_value",
                            "result": "WARNING",
                            "detail": (
                                "Candidate is compatible but only adds pipeline audit tables; "
                                "app-facing core tables are unchanged. Promotion is not necessary yet."
                            ),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    table_summary.to_csv(output_dir / "db_table_summary.csv", index=False, encoding="utf-8-sig")
    schema_comparison.to_csv(output_dir / "db_schema_comparison.csv", index=False, encoding="utf-8-sig")
    yearly_totals.to_csv(output_dir / "db_yearly_totals_comparison.csv", index=False, encoding="utf-8-sig")
    source_comparison.to_csv(output_dir / "db_source_comparison.csv", index=False, encoding="utf-8-sig")
    company_top20.to_csv(output_dir / "db_company_comparison_top20.csv", index=False, encoding="utf-8-sig")
    lob_top20.to_csv(output_dir / "db_lob_comparison_top20.csv", index=False, encoding="utf-8-sig")
    soat.to_csv(output_dir / "db_soat_comparison.csv", index=False, encoding="utf-8-sig")
    bolivar.to_csv(output_dir / "db_bolivar_comparison.csv", index=False, encoding="utf-8-sig")
    bolivar_fire.to_csv(output_dir / "db_bolivar_incendio_lucro_comparison.csv", index=False, encoding="utf-8-sig")
    reinsurance.to_csv(output_dir / "db_reinsurance_comparison.csv", index=False, encoding="utf-8-sig")
    checks.to_csv(output_dir / "db_critical_checks.csv", index=False, encoding="utf-8-sig")

    _write_summary(output_dir, doc_path, checks, recommendation, table_summary, schema_comparison, yearly_totals)
    return {
        "recommendation": recommendation,
        "checks": checks,
        "output_dir": output_dir,
        "doc_path": doc_path,
    }


def main() -> int:
    result = compare_databases()
    print(f"Candidate database review complete.")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Outputs: {result['output_dir']}")
    print(result["checks"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
