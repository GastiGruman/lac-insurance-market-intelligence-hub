# Formato 290 Regulatory Data Pipeline

## Purpose

The Formato 290 pipeline creates an auditable regulatory data flow for Colombia using Datos Abiertos Colombia dataset `e967-4a8r`.

It is designed to:

- verify the official dataset metadata,
- download all rows through Socrata pagination,
- save a raw audit copy,
- load raw data into DuckDB,
- normalize the wide ramo structure into a long analytical table,
- map official concepts into business metrics,
- create marts for premiums, claims, commissions, reinsurance and technical result,
- create a dashboard-compatible core table,
- write validation, data quality and reconciliation outputs.

## Manual run

From Windows CMD or PowerShell:

```powershell
cd "C:\Users\PC\Documents\colombia_insurance_market_dashboard - copia"
python scripts\update_formato_290.py
```

Then run the app:

```powershell
streamlit run app\streamlit_app.py
```

## Files generated

- Raw audit file: `data/raw/formato_290/formato_290_raw_YYYYMMDD_HHMMSS.csv`
- Log: `logs/formato_290_update.log`
- Column inventory: `outputs/data_dictionary/formato_290_columns.csv`
- Concept inventory: `outputs/data_dictionary/formato_290_concepts.csv`
- Company coverage: `outputs/data_quality/formato_290_company_completeness.csv`
- Ramo coverage: `outputs/data_quality/formato_290_ramo_completeness.csv`
- Period coverage: `outputs/data_quality/formato_290_period_coverage.csv`
- Null checks: `outputs/data_quality/formato_290_null_checks.csv`
- Validation: `outputs/validation/formato_290_validation_results.csv`
- Latest status: `outputs/validation/formato_290_latest_status.csv`
- Reconciliation template: `data/reference/formato_290_reconciliation_template.csv`

## DuckDB tables

- `raw_formato_290`
- `clean_formato_290`
- `formato_290_metric_mapping_status`
- `mart_formato_290_dashboard_metrics`
- `mart_formato_290_premiums`
- `mart_formato_290_claims`
- `mart_formato_290_commissions`
- `mart_formato_290_reinsurance`
- `mart_formato_290_technical_result`
- `fact_market_core_formato_290`
- `validation_formato_290`

## Metric mapping

Metric mapping is keyword-based and transparent in `app/config/formato_290_metric_mapping.py`. Any concept that does not match the mapping rules remains `pending_mapping` and is visible in Data Status and the mapping report.

Business review is required for:

- whether values are monthly, year-to-date or annual,
- whether gross/direct/earned premium definitions are correct,
- whether claims should use incurred, paid or another technical account,
- whether commissions, intermediation and technical result are complete enough for dashboard use.

## Safety

The script creates a DuckDB backup before replacing Formato 290 tables. It does not delete legacy Fasecolda tables. The app prefers the Formato 290 core table only when it exists; otherwise it shows a visible fallback warning in Data Status.

## Scheduling

Recommended current approach: manual controlled update.

Future options:

- Windows Task Scheduler for local refreshes.
- Internal server or VM for controlled corporate refreshes.
- GitHub Actions only after data storage and credentials policy are agreed.
- Managed cloud job once the platform is production-hosted.

