# Project Status - LAC Insurance Market Intelligence Hub

## Current Phase

**Phase 4B - Advanced broker-focused Reinsurance View**

The Colombia MVP is deployed as a Streamlit Cloud demo for limited internal broker testing. The current focus is improving the Reinsurance View as a treaty-broker module while preserving the stable demo database, the advanced Company Brief, and the manual Phase 3 pipeline.

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
| Phase 3B | Candidate database review and promotion readiness | In progress in this branch | Compares candidate DuckDB against stable demo DB and blocks promotion unless review recommends it. |
| Phase 4 | Broker-focused refinements | In progress | Phase 4A improved Company Brief; Phase 4B improves Reinsurance View as a treaty-broker module using structured internal data. |
| Phase 5 | Controlled AI module | Planned | AI outputs must be grounded in structured data and approved sources. |
| Phase 6 | Company news module | Planned | Source-based news and broker relevance, with provider configuration. |

## Current Sources

### Fasecolda - Ciudades y Ramos

Status: core source for the Colombia MVP.

Used for:

- Premiums.
- Claims.
- Claims / Premiums analytical ratio.
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
- Candidate DuckDB promotion is controlled by a review workflow and explicit approval.
- Not yet corporate-hosted.
- Not yet reviewed as a production data product by IT/Data/Compliance.
- AI and news providers are not part of Phase 2.
- Figures must be validated before formal external presentation.
- The app's Claims / Premiums ratio is an analytical `claims / gross_written_premium` metric. It should not be interpreted as Fasecolda's official technical siniestralidad, technical loss ratio, or combined ratio unless specifically stated.
- SOAT should be reviewed carefully because official Fasecolda technical views may include components not captured by a simple claims/premiums ratio.

## Future Enhancement

Add a separate official technical indicator module using Fasecolda - Indicadores de Gestion where available and methodologically confirmed. The app should eventually show both:

- Claims / Premiums analytical ratio.
- Official technical indicator or combined ratio, when available and validated.

## Ready For

- Limited internal testing with 2-3 brokers.
- Feedback on usefulness, terminology, workflow, and trust.
- Review of source traceability and methodology.
- Broker review of the advanced Company Brief and Reinsurance View workflows for meeting preparation.

## Not Yet Ready For

- Broad internal rollout.
- External client use without review.
- Production data refreshes.
- Unattended automated regulatory pipeline operation.
- Formal actuarial, legal, accounting, or financial reporting.

## Phase 4A - Advanced Broker-Focused Company Brief

The Company Brief has been improved as the main broker preparation page. It now emphasizes:

- Executive snapshot.
- Market position and rank.
- Main competitors.
- Portfolio mix and concentration.
- Premium and Claims / Premiums evolution.
- Broker-oriented technical alerts.
- Compact exploratory reinsurance signals where available.
- Suggested meeting questions based on structured app data.

The brief remains based on DuckDB, public Fasecolda data, mappings and calculated app metrics. External intelligence, leadership context and news are reserved for later AI Brief and News phases.

## Phase 4B - Advanced Broker-Focused Reinsurance View

The Reinsurance View has been improved as a treaty-broker preparation module. It now emphasizes:

- Executive reinsurance snapshot.
- Company vs market cession and retention benchmark where available.
- Top ceded lines and ceded-premium concentration.
- Cession, retention and paid-claims indicators by line.
- Available evolution over time, with a clear notice when only one reinsurance year is available.
- Broker-oriented treaty signals and suggested reinsurance questions.
- Methodology notes that keep Indicadores de Gestion 2025 exploratory and source-dependent.

The view remains based on structured DuckDB data, public Fasecolda data and mapping tables. It does not use AI interpretation, external news, or private client information.
