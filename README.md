# LAC Insurance Market Intelligence Hub - Colombia MVP

Internal Streamlit MVP for insurance market intelligence, starting with Colombia and public Fasecolda data.

## What The App Does

The app helps reinsurance brokers prepare meetings and understand market movements through:

- Market premium, claims, and loss-ratio views.
- Company and line-of-business exploration.
- Broker-focused company briefs.
- Technical signals.
- Exploratory reinsurance indicators.
- Data status, traceability, and validation visibility.
- Filtered exports for internal analysis.

## Current Scope

- Country: Colombia.
- Source: public Fasecolda data.
- Deployment: Streamlit Cloud demo branch.
- Data storage: DuckDB snapshot at `data/database/insurance_market.duckdb`.
- Current phase: Phase 2 - data methodology and trust layer.

The demo is a static snapshot. It does not yet update automatically from Fasecolda.

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

## Documentation

- `docs/data_dictionary.md`
- `docs/methodology.md`
- `docs/source_to_module_matrix.md`
- `docs/mapping_methodology.md`
- `docs/data_validation_notes.md`
- `docs/project_status.md`

## Completed

- Phase 1: Colombia MVP stability for Streamlit Cloud demo testing.
- Phase 2: Data methodology, traceability, validation notes, mapping documentation, and trust layer.

## Planned

- Phase 3: Automatic Fasecolda ingestion pipeline.
- Phase 4: Broker-focused refinements based on internal feedback.
- Phase 5: Controlled AI module.
- Phase 6: Source-based company news module.

## Current Limitations

- Static database snapshot.
- Not yet a corporate-hosted production service.
- Not yet automatically updated.
- AI and news modules are placeholders unless providers are configured.
- Figures should be validated against source files before formal external use.
