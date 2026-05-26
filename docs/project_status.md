# Project Status - LAC Insurance Market Intelligence Hub

## Current Phase

**Source-of-truth migration - SFC Formato 290 foundation**

The Colombia MVP is deployed as a Streamlit Cloud demo for limited internal broker testing. The current focus is correcting the Colombia data foundation by adding an official SFC Formato 290 ingestion, validation and reconciliation workflow.

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
| Phase 3A | Manual Fasecolda ingestion pipeline | Completed in this branch | Manual-run pipeline structure, fallback source registry, metadata, validations, and safe DuckDB candidate strategy. |
| Phase 3B | Candidate database review and promotion readiness | Completed in this branch | Compares candidate DuckDB against stable demo DB and blocks promotion unless review recommends it. |
| Phase 4 | Broker-focused refinements | Completed in this branch | Phase 4A improved Company Brief; Phase 4B improved Reinsurance View; Phase 4C connects AI Brief to internal structured data; Phase 4D adds curated/manual external intelligence; Phase 4E adds broker reports and exports; Phase 4F adds operational readiness. |
| Phase 5A | UX / visual polish for internal v1 | Completed in this branch | Improves header, navigation wording, module headers, empty states, Data Status readability and export usability without changing calculations. |
| Source migration | SFC Formato 290 pipeline | In progress | Adds Datos Abiertos Colombia dataset `e967-4a8r` ingestion, raw/clean/mart tables, validation outputs, reconciliation template and Data Status visibility. |
| Phase 5B | Controlled external AI module | Planned | Future LLM outputs must be grounded in structured data and approved sources. |
| Phase 6 | Live company news module | Planned | Future source-based live news retrieval with approved provider configuration. |

## Current Sources

### SFC Formato 290 / Datos Abiertos Colombia

Status: target source of truth for Colombia core market metrics.

Dataset:

- Name: Informacion estadistica y financiera por ramos de seguros Formato 290.
- Dataset ID: `e967-4a8r`.
- Provider: Superintendencia Financiera de Colombia.
- API: `https://www.datos.gov.co/resource/e967-4a8r.json`.

Used for after ingestion and validation:

- Premium bases.
- Claims bases.
- Commissions/intermediation if mapped.
- Technical result if mapped.
- Ramo/company/period coverage.
- Future core market dashboard metrics.

Limitations:

- Concept mapping requires business review.
- Period basis must be confirmed before annualizing values.
- Reconciliation against official reference values is required before formal use.

### Fasecolda - Ciudades y Ramos

Status: legacy fallback until Formato 290 is ingested and validated.

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
- Broker review of the internal-data AI Brief workflow for meeting preparation.
- Broker review of curated/manual News and External Intelligence workflow.
- Broker review of copy-ready Reports / Export outputs.
- Controlled monthly maintenance dry run using the maintenance runbook.
- IT/Data discussion about future scheduling and corporate hosting.

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

## Phase 4C - Internal-Data AI Brief

The AI Brief has been connected to internal structured app data. It now generates a deterministic broker-ready brief without requiring an external AI provider.

It uses:

- Selected filters for country, company, line and years.
- Market Overview context.
- Company Brief context.
- Reinsurance View context.
- Technical signals and methodology limitations.

It does not use internet, company news, ratings, financial statements, key people, leadership data or live LLM interpretation. Those items remain future external-intelligence phases.

## Phase 4D - Curated Company News / External Intelligence

The News module has been converted into a safe curated/manual external intelligence layer. It now reads a small committed template file under `data/external/` and does not require external APIs, secrets, scraping, or internet access.

It supports:

- Selected company context.
- Curated news item structure with source, date, link, category and broker relevance.
- Summary cards for item count, latest date, top category and verified/manual items.
- Broker interpretation and suggested questions.
- Key people / leadership placeholder without inventing names.
- Clear limitations that external intelligence is contextual and must be validated before formal use.

Live provider-based news retrieval remains a future governed enhancement.

## Phase 4E - Broker Reports / Export Center

Reports / Export has been upgraded into a practical export center for broker workflows. It supports:

- Company Brief markdown / HTML.
- Internal-data AI Brief markdown / HTML.
- Reinsurance Summary markdown / HTML.
- Market Summary markdown / HTML.
- Broker One-Pager markdown / HTML.
- PPT-ready bullets as copy-ready markdown text.
- Filtered data CSV.
- Filtered data Excel when runtime support is available.
- Additional annual, company and reinsurance CSV summaries.

Exports are generated in memory and include methodology notes. PDF and actual PowerPoint generation remain future enhancements.

## Phase 4F - Operational Maintenance Readiness

Operational readiness has been added to support controlled maintenance and future handoff to IT/Data. This phase adds:

- Maintenance runbook for routine updates.
- Scheduled automation plan with manual, local scheduler, internal server, GitHub Actions and managed cloud options.
- Release checklist for safe commits and Streamlit Cloud reboots.
- Operational status document.
- Read-only maintenance check script.
- Clearer Data Status wording for manual pipeline mode, static demo snapshot, and manual candidate promotion.

No scheduler has been activated. No external service, credential, or secret has been added. The current demo database remains the stable static snapshot unless a future candidate promotion is explicitly approved.

## Phase 5A - UX / Visual Polish For Internal v1

The Streamlit app has been polished for internal presentation readiness. This phase improves:

- Top header and status line.
- Sidebar wording and module grouping.
- Filter helper text and clearer empty states.
- Consistent module headers with broker-oriented purpose statements.
- More consistent Claims / Premiums, premium, market share, cession and retention wording.
- Data Status grouping for data mode, source coverage, pipeline status and methodology limitations.
- Reports / Export file naming and preview flow.

No database, calculation, external API, live news, or AI API behavior was changed.
