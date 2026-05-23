# Roadmap - LAC Insurance Market Intelligence Hub

## Phase 1 - Colombia MVP Stability

Status: completed.

Focus:

- Stable Streamlit Cloud demo.
- Defensive filters.
- Lazy navigation.
- Friendly warnings instead of app crashes.
- Demo branch with DuckDB snapshot.

## Phase 2 - Colombia Methodology and Trust Layer

Status: completed in this branch.

Focus:

- Data dictionary.
- Methodology notes.
- Source-to-module traceability.
- Mapping methodology.
- Validation notes.
- Improved Data Status transparency.

## Phase 3 - Automatic Fasecolda Data Ingestion Pipeline

Status: in progress in this branch.

Focus:

- Download or retrieve public Fasecolda files.
- Detect new periods.
- Normalize and validate files.
- Update DuckDB safely.
- Produce logs and validation reports.
- Prevent bad loads from replacing trusted data.

Initial implementation:

- Official Fasecolda landing pages configured.
- Manual source registry fallback.
- Download manifest.
- Normalized processed outputs.
- Mapping integration and unmapped review files.
- Pipeline validation reports.
- Candidate DuckDB strategy with explicit promotion flag.

## Phase 4 - Broker-Focused Refinements

Status: planned.

Focus:

- Internal user feedback.
- Meeting-prep workflows.
- Cleaner reports.
- Better signal thresholds.
- More explicit caveats where needed.

## Phase 5 - Controlled AI Module

Status: planned.

Focus:

- Use only structured data and approved sources.
- No invented facts.
- Clear source and period citations.
- Broker meeting preparation support.

## Phase 6 - Company News Module

Status: planned.

Focus:

- Source-based company and market news.
- Regulatory and rating-action monitoring where available.
- Broker relevance summaries.
- Verification warnings before client use.

## Phase 7 - Regional Expansion

Status: future.

Potential countries:

- Colombia.
- Mexico.
- Chile.
- Peru.
- Argentina.
- Costa Rica.
- Panama.
- Ecuador.
- Dominican Republic.

Regional expansion will require country-by-country source review, mapping methodology, currency treatment, and regulatory context.
