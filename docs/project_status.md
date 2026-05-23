# Project Status - LAC Insurance Market Intelligence Hub

## Current Phase

**Phase 3 - Automated regulatory ingestion pipeline**

The Colombia MVP is deployed as a Streamlit Cloud demo for limited internal broker testing. Phase 3 adds the first manual-run automated Fasecolda ingestion pipeline: source discovery, download manifesting, processing, validation, pipeline status, and safe DuckDB candidate creation.

## Design Principle

**Regional by design. Colombia-rich where possible. Broker-focused always.**

## Current Deployment

- App framework: Streamlit.
- Database: DuckDB.
- Branch: `demo-streamlit-cloud`.
- Main file: `app/streamlit_app.py`.
- Data update mode: static demo snapshot with manual pipeline metadata.
- Automatic updates: manual-run pipeline available; scheduled automation not yet enabled.
- Corporate hosting: not yet implemented.

## Phase Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| Phase 1 | Colombia MVP stability | Completed | Streamlit Cloud demo stabilized with defensive filters, lazy navigation, and friendly warnings. |
| Phase 2 | Colombia reliable / trust layer | Completed in this branch | Data dictionary, methodology, validation notes, mapping methodology, and source-to-module traceability added or updated. |
| Phase 3 | Automatic Fasecolda data ingestion pipeline | In progress in this branch | Manual-run pipeline structure, fallback source registry, metadata, validations, and safe DuckDB candidate strategy. |
| Phase 4 | Broker-focused refinements | Planned | Improve workflows after feedback from internal users. |
| Phase 5 | Controlled AI module | Planned | AI outputs must be grounded in structured data and approved sources. |
| Phase 6 | Company news module | Planned | Source-based news and broker relevance, with provider configuration. |

## Current Sources

### Fasecolda - Ciudades y Ramos

Status: core source for the Colombia MVP.

Used for:

- Premiums.
- Claims.
- Loss ratio.
- Market share.
- Growth.
- Company, line, city, and year filters.
- Company and line exploration.
- Data table and exports.

Methodology:

- `VALOR` is treated as thousands of COP and converted to COP in the app.
- Monthly files are treated as cumulative period cuts.
- Annual views use the latest available month for each selected year.

### Fasecolda - Indicadores de Gestion 2025

Status: complementary exploratory source.

Used for:

- Reinsurance View.
- Retained premium.
- Reinsurance ceded premium.
- Cession ratio.
- Retention ratio.
- Paid claims.

Limitations:

- Requires deeper methodology review before production integration.
- Aggregate lines can duplicate individual lines.
- Ratios must be recalculated after aggregation.

## Mapping Tables

Formal mapping tables are included:

- `dim_company_mapping`
- `dim_line_of_business_mapping`

Mapping CSVs are maintained under `data/mappings/`.

These mappings align source-specific names to standard app names. They support cross-source comparison between Ciudades y Ramos and Indicadores de Gestion.

## Validation

Validation scripts are available under `src/`. Validation output files are not committed to the demo branch because `outputs/` is excluded. The app shows whether validation files are available in Data Status.

Warnings should be interpreted as review signals, not automatic rejection of the data.

## Current Limitations

- Static DuckDB snapshot included for Streamlit Cloud demo.
- No scheduled Fasecolda refresh yet; Phase 3 pipeline is manual-run.
- Not yet corporate-hosted.
- Not yet reviewed as a production data product by IT/Data/Compliance.
- AI and news providers are not part of Phase 2.
- Figures must be validated before formal external presentation.

## Ready For

- Limited internal testing with 2-3 brokers.
- Feedback on usefulness, terminology, workflow, and trust.
- Review of source traceability and methodology.

## Not Yet Ready For

- Broad internal rollout.
- External client use without review.
- Production data refreshes.
- Unattended automated regulatory pipeline operation.
- Formal actuarial, legal, accounting, or financial reporting.
