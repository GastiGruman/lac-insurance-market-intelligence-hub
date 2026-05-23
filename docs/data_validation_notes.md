# Data Validation Notes - Colombia MVP

## Purpose

Validation is designed to help brokers and internal reviewers understand data quality risks before relying on outputs. Warnings are signals for review, not automatic rejection of the data.

## Current Validation Coverage

Validation scripts include:

- `src/validate_market_core.py`
- `src/validate_indicadores_gestion_2025.py`

The Streamlit Cloud demo does not commit `outputs/`, so validation reports may not always be visible in the deployed app. Data Status will show whether validation files are available.

## Core Market Validation

The core market table is checked for:

- Expected columns.
- Missing or null key fields.
- Missing metric values.
- Date coverage.
- Metric availability.
- Source-file traceability.
- Company, line, and city coverage.

## Reinsurance Source Validation

Indicadores de Gestion 2025 is checked for:

- `gross_written_premium <= 0`
- `retained_premium > gross_written_premium`
- `reinsurance_ceded_premium < 0`
- `retention_ratio` outside expected range
- `reinsurance_cession_ratio` outside expected range
- `paid_claims_ratio` above expected threshold
- Aggregate lines
- Possible duplicated aggregate impact
- Difference between extracted and recalculated retention ratio
- Difference between extracted and recalculated cession ratio

## Ratio Validation

Ratios are recalculated after aggregation. This matters because summing ratios produces misleading results. When extracted ratios differ materially from recalculated ratios, the app flags the record for review.

The app's core market ratio labelled Claims / Premiums or Siniestros / Primas is calculated as `claims / gross_written_premium` from the normalized app database. It is not automatically equivalent to Fasecolda's official technical siniestralidad, incurred loss ratio, paid loss ratio, or combined ratio. SOAT and other technical or regulated lines should be reviewed carefully before comparing app outputs to Fasecolda visualizer indicators.

## Premium and Retention Checks

A retained premium greater than gross written premium may indicate:

- Source interpretation issue.
- Extraction or mapping issue.
- Special accounting or reporting treatment.

It should be reviewed, not automatically discarded.

## Negative and Out-of-Range Values

Negative or out-of-range values can occur because of corrections, cancellations, reporting conventions, or extraction issues. The validation process flags these records so a reviewer can decide whether they are acceptable for the analytical context.

## Aggregate Line Warnings

Aggregate lines can duplicate individual lines in rankings and totals. Reinsurance View excludes aggregate lines by default to reduce duplicated impact. Users can include them only for source inspection.

## Broker Interpretation

Validation warnings should help brokers ask better questions:

- Is the movement real or a source/classification effect?
- Is a ratio distorted by a small premium base?
- Is a line aggregate duplicating individual lines?
- Does a company name mapping need review?
- Should the number be reconciled before client use?

For formal client or market presentations, figures should be validated against original Fasecolda source files and internal review standards.
