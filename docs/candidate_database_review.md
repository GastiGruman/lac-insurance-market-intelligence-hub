# Candidate Database Review

- Review date/time: 2026-05-23 14:54:48
- Current DB path: `data/database/insurance_market.duckdb`
- Candidate DB path: `data/database/insurance_market_candidate.duckdb`
- Pipeline mode used for candidate: `update-db`
- Promotion recommendation: **Do not promote yet**

## Critical Checks

| check_name | result | detail |
| --- | --- | --- |
| candidate_exists | PASS | C:\Users\PC\Documents\colombia_insurance_market_dashboard - copia\data\database\insurance_market_candidate.duckdb |
| required_app_tables | PASS | All required app tables exist. |
| required_fact_market_core_columns | PASS | All required fact_market_core columns exist. |
| app_schema_compatibility | PASS | Required app table schema is compatible. |
| fact_market_core_row_count | PASS | Current rows: 1,293,272; candidate rows: 1,293,272; diff pct: 0.0000% |
| year_range | PASS | Current: 2015-2025; candidate: 2015-2025 |
| yearly_premium_claims_reconciliation | PASS | Yearly premium and claims totals are within tolerance. |
| promotion_value | WARNING | Candidate is compatible but only adds pipeline audit tables; app-facing core tables are unchanged. Promotion is not necessary yet. |

## Main Differences

- Extra candidate tables: pipeline_ciudades_ramos_normalized, pipeline_indicadores_gestion_normalized
- Current fact_market_core rows: 1,293,272
- Candidate fact_market_core rows: 1,293,272
- Max yearly premium difference pct: 0.000000%
- Max yearly claims difference pct: 0.000000%

## Interpretation

The candidate database is compared against the current stable demo database before any promotion. This candidate is app-compatible if all critical checks pass. However, if it only copies the current app tables and adds pipeline audit tables, promotion is operationally unnecessary until the pipeline is ready to rebuild or refresh the app-facing tables.

## Required Next Actions

- Review generated reconciliation files under `data/metadata/db_comparison/` locally.
- Test the app against the candidate with `USE_CANDIDATE_DB=true` before any promotion.
- Promote only after explicit approval and only if the recommendation is `Promote now`.
