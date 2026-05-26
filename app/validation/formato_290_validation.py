from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def validation_row(check_name: str, status: str, details: str, affected_rows: int | None = None) -> dict[str, Any]:
    return {
        "check_name": check_name,
        "status": status,
        "details": details,
        "affected_rows": affected_rows,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def validate_formato_290_frames(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    mapping_status_df: pd.DataFrame,
    dashboard_df: pd.DataFrame,
) -> pd.DataFrame:
    results: list[dict[str, Any]] = []
    results.append(
        validation_row(
            "dataset_downloaded",
            "PASS" if not raw_df.empty else "FAIL",
            f"Raw rows downloaded: {len(raw_df):,}",
            len(raw_df),
        )
    )
    results.append(
        validation_row(
            "clean_rows_available",
            "PASS" if not clean_df.empty else "FAIL",
            f"Clean long-form rows: {len(clean_df):,}",
            len(clean_df),
        )
    )

    for col in ["year", "month", "company_name", "ramo", "concept_name", "normalized_value"]:
        if col not in clean_df.columns:
            results.append(validation_row(f"required_column_{col}", "FAIL", f"Missing column: {col}"))
        else:
            nulls = int(clean_df[col].isna().sum())
            results.append(
                validation_row(
                    f"null_check_{col}",
                    "PASS" if nulls == 0 else "WARNING",
                    f"Null rows in {col}: {nulls:,}",
                    nulls,
                )
            )

    if "normalized_value" in clean_df.columns:
        invalid_numeric = int(pd.to_numeric(clean_df["normalized_value"], errors="coerce").isna().sum())
        results.append(
            validation_row(
                "numeric_values_valid",
                "PASS" if invalid_numeric == 0 else "WARNING",
                f"Rows with invalid numeric value: {invalid_numeric:,}",
                invalid_numeric,
            )
        )

    if {"year", "month"}.issubset(clean_df.columns) and not clean_df.empty:
        latest = clean_df[["year", "month"]].dropna().sort_values(["year", "month"]).tail(1)
        details = "Latest period could not be detected." if latest.empty else f"Latest period: {int(latest.iloc[0]['year'])}-{int(latest.iloc[0]['month']):02d}"
        results.append(validation_row("latest_period_detected", "PASS" if not latest.empty else "FAIL", details))

    mapped = set(mapping_status_df.loc[mapping_status_df["status"] == "MAPPED", "metric_name"]) if not mapping_status_df.empty else set()
    for metric in ["gross_written_premium", "earned_premium", "claims_incurred", "claims_paid", "commissions", "technical_result"]:
        status = "PASS" if metric in mapped else "WARNING"
        results.append(validation_row(f"metric_mapping_{metric}", status, f"{metric}: {'mapped' if metric in mapped else 'pending/unavailable'}"))

    if not dashboard_df.empty and {"metric_name", "metric_value"}.issubset(dashboard_df.columns):
        premium = dashboard_df.loc[dashboard_df["metric_name"].isin(["gross_written_premium", "earned_premium"]), "metric_value"].sum()
        claims = dashboard_df.loc[dashboard_df["metric_name"].isin(["claims_incurred", "claims_paid"]), "metric_value"].sum()
        if premium and premium > 0:
            results.append(validation_row("loss_ratio_from_totals", "PASS", f"Claims / premium denominator is positive. Total ratio: {claims / premium:.4f}"))
        else:
            results.append(validation_row("loss_ratio_denominator_valid", "WARNING", "Premium denominator is zero, negative or unavailable."))
    else:
        results.append(validation_row("dashboard_metrics_available", "WARNING", "Dashboard mart is empty or missing metric columns."))

    results.append(
        validation_row(
            "period_basis_review",
            "WARNING",
            "Formato 290 period basis must be reviewed with business/SFC documentation before annualizing values.",
        )
    )
    return pd.DataFrame(results)

