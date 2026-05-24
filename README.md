# LAC Insurance Market Intelligence Hub - Colombia MVP

Internal Streamlit MVP for insurance market intelligence, starting with Colombia and public Fasecolda data.

## What The App Does

The app helps reinsurance brokers prepare meetings and understand market movements through:

- Market premium, claims, and loss-ratio views.
- Company and line-of-business exploration.
- Broker-focused company briefs.
- Technical signals.
- Exploratory reinsurance indicators.
- Internal-data AI Brief.
- Curated/manual company news and external intelligence.
- Broker-ready reports and lightweight exports.
- Data status, traceability, and validation visibility.
- Filtered exports for internal analysis.

## Current Scope

- Country: Colombia.
- Source: public Fasecolda data.
- Deployment: Streamlit Cloud demo branch.
- Data storage: DuckDB snapshot at `data/database/insurance_market.duckdb`.
- Current phase: Phase 4F - operational maintenance readiness.

The demo still runs from a static DuckDB snapshot on Streamlit Cloud. Phase 3 adds a manual-run Fasecolda ingestion pipeline and pipeline status metadata. Phase 4F adds the maintenance runbook, release checklist, operational status, and scheduling plan. Scheduled automatic refreshes are not yet enabled.

## Main Sources

- **Fasecolda - Ciudades y Ramos**: core source for premiums, claims, companies, lines of business, cities, and annual trends.
- **Fasecolda - Indicadores de Gestion 2025**: complementary exploratory source for reinsurance indicators such as retained premium, ceded premium, cession ratio, retention ratio, and paid claims.

## Important Methodology Notes

- Ciudades y Ramos `VALOR` is treated as thousands of COP and converted to COP in the app.
- App labels such as `COP MM` show millions of COP after conversion.
- Monthly Ciudades y Ramos files are treated as cumulative period cuts.
- Annual views use the latest available monthly cut per selected year.
- Ratios are recalculated after aggregation and are not summed.
- Reinsurance indicators are exploratory and should be validated before formal use.

## Run Locally

```powershell
cd "C:\Users\PC\Documents\colombia_insurance_market_dashboard - copia"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app\streamlit_app.py
```

## Streamlit Cloud Deployment

Use:

- Repository: `GastiGruman/lac-insurance-market-intelligence-hub`
- Branch: `demo-streamlit-cloud`
- Main file path: `app/streamlit_app.py`

The demo branch intentionally includes only the small DuckDB demo snapshot required for the deployed app. Raw data, processed data, outputs, secrets, and virtual environments are excluded.

## Operational Maintenance

Run the app locally:

```powershell
python -m streamlit run app\streamlit_app.py
```

Run the manual Fasecolda pipeline:

```powershell
python -m src.pipeline.run_colombia_pipeline --mode discover
python -m src.pipeline.run_colombia_pipeline --mode validate
python -m src.pipeline.run_colombia_pipeline --mode update-db
```

Review a candidate database before any promotion:

```powershell
python -m src.pipeline.compare_candidate_database
```

Run the read-only maintenance check:

```powershell
python -m src.pipeline.maintenance_check
```

Operational references:

- `docs/maintenance_runbook.md`
- `docs/release_checklist.md`
- `docs/operational_status.md`
- `docs/scheduled_automation_plan.md`

Current recommendation: keep manual controlled updates until IT/Data approves an internal server, VM, or managed scheduler.

## Documentation

- `docs/data_dictionary.md`
- `docs/methodology.md`
- `docs/source_to_module_matrix.md`
- `docs/mapping_methodology.md`
- `docs/data_validation_notes.md`
- `docs/automated_data_pipeline.md`
- `docs/news_module.md`
- `docs/reports_export_module.md`
- `docs/maintenance_runbook.md`
- `docs/release_checklist.md`
- `docs/operational_status.md`
- `docs/scheduled_automation_plan.md`
- `docs/project_status.md`

## Completed

- Phase 1: Colombia MVP stability for Streamlit Cloud demo testing.
- Phase 2: Data methodology, traceability, validation notes, mapping documentation, and trust layer.
- Phase 3: First automated regulatory ingestion pipeline structure, manual source discovery/download/processing/validation flow, and safe DuckDB candidate strategy.
- Phase 4A-4F: Broker-focused Company Brief, Reinsurance View, internal-data AI Brief, curated/manual external intelligence, broker Reports / Export Center, and operational maintenance readiness.

## Planned

- Phase 5: Controlled external AI module.
- Phase 6: Approved live news provider integration.

## Current Limitations

- Static database snapshot.
- Not yet a corporate-hosted production service.
- Pipeline can be run manually, but scheduled automatic updates are not yet enabled.
- AI Brief works from internal structured data without external API keys.
- News / External Intelligence uses curated/manual template files and is not a live news feed yet.
- Figures should be validated against source files before formal external use.
