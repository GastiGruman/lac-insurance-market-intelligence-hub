from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data/database/insurance_market.duckdb"
REFERENCE_PATH = PROJECT_ROOT / "data/reference/formato_290_reconciliation_template.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs/reconciliation/formato_290_reconciliation_report.csv"


def dashboard_value(conn: duckdb.DuckDBPyConnection, metric_name: str, period: str, company: str, ramo: str) -> float | None:
    filters = ["metric_name = ?"]
    params: list[object] = [metric_name]
    if period:
        filters.append("strftime(period_date, '%Y-%m') = ?")
        params.append(period[:7])
    if company:
        filters.append("company_standard = ?")
        params.append(company.strip().upper())
    if ramo:
        filters.append("ramo_standard = ?")
        params.append(ramo.strip().upper())
    where = " AND ".join(filters)
    result = conn.execute(
        f"SELECT SUM(metric_value) FROM mart_formato_290_dashboard_metrics WHERE {where}",
        params,
    ).fetchone()[0]
    return None if result is None else float(result)


def main() -> int:
    if not REFERENCE_PATH.exists():
        print(f"Reference template not found: {REFERENCE_PATH}")
        print("Run python scripts/update_formato_290.py first to create the template.")
        return 1
    references = pd.read_csv(REFERENCE_PATH)
    if references.empty:
        print(f"Reference file is empty. Populate it first: {REFERENCE_PATH}")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    rows = []
    try:
        for _, row in references.iterrows():
            metric = str(row.get("metric_name", "")).strip()
            value = dashboard_value(
                conn,
                metric,
                str(row.get("period", "") or "").strip(),
                str(row.get("company", "") or "").strip(),
                str(row.get("ramo", "") or "").strip(),
            )
            official = pd.to_numeric(row.get("official_value"), errors="coerce")
            diff = value - official if pd.notna(official) and value is not None else pd.NA
            pct = diff / official if pd.notna(diff) and official not in (0, 0.0) else pd.NA
            tol_abs = pd.to_numeric(row.get("tolerance_absolute"), errors="coerce")
            tol_pct = pd.to_numeric(row.get("tolerance_percentage"), errors="coerce")
            status = "WARNING"
            if pd.notna(diff):
                abs_ok = pd.isna(tol_abs) or abs(diff) <= tol_abs
                pct_ok = pd.isna(tol_pct) or (pd.notna(pct) and abs(pct) <= tol_pct)
                status = "PASS" if abs_ok and pct_ok else "FAIL"
            output = row.to_dict()
            output.update(
                {
                    "dashboard_value": value,
                    "difference": diff,
                    "percentage_difference": pct,
                    "status": status,
                }
            )
            rows.append(output)
    finally:
        conn.close()
    pd.DataFrame(rows).to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Reconciliation report written to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

