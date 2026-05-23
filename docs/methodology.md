# Methodology - Colombia MVP

## Purpose

The LAC Insurance Market Intelligence Hub is designed to help reinsurance brokers prepare client meetings, understand market movements, and identify questions worth discussing with insurers. The current MVP is Colombia-first because public Fasecolda data provides enough detail to build a useful pilot.

The platform is broker-focused market intelligence. It is not a legal, actuarial, accounting, or financial advice tool.

## Current Scope

- Country: Colombia.
- Deployment: Streamlit Cloud demo branch.
- Data update mode: static DuckDB snapshot included in the demo branch.
- Automatic updates: not yet enabled. Automatic Fasecolda ingestion is planned for Phase 3.
- Primary data model: DuckDB tables consumed by Streamlit.

## Why Public Fasecolda Data Is Used

Fasecolda publishes public market data that can support a first market intelligence layer without using confidential client information. This makes it appropriate for an MVP that is safe to test internally while still being useful for broker preparation.

## Source 1: Fasecolda - Ciudades y Ramos

This is the core source for the Colombia market dashboard. It supports:

- Market Overview.
- Company Explorer.
- Line of Business Explorer.
- Company Brief.
- Technical Signals.
- Reports / Export.
- Data Table.

Main fields used:

- Company.
- Line of business.
- City.
- Premiums.
- Claims.
- Reporting period.
- Source file.

### Premiums and Claims

The source field `VALOR` is treated as thousands of COP and converted to COP in the app. App labels such as `COP MM` show millions of COP after that conversion.

Monthly Ciudades y Ramos files are treated as cumulative reporting cuts. Annual app views use the latest available monthly cut for each selected year instead of summing every monthly file. This avoids double-counting year-to-date values.

## Source 2: Fasecolda - Indicadores de Gestion 2025

This is a complementary exploratory source used mainly for reinsurance indicators. It supports:

- Reinsurance View.
- Reinsurance indicators in Company Brief when mappings are available.
- Reinsurance summary exports.
- Some technical signals related to cession ratio.

Main fields used:

- Gross written premium.
- Retained premium.
- Reinsurance ceded premium.
- Paid claims.
- Cession ratio.
- Retention ratio.

This source is not yet part of the core regional model. It requires further methodological review before formal production use.

## Ratio Calculations

Ratios are recalculated at the selected aggregation level. They are not summed.

| Ratio | Calculation |
|---|---|
| Claims / Premiums | `claims / gross_written_premium` |
| Market share | `company gross_written_premium / selected market gross_written_premium` |
| Premium growth | `current period premium / previous period premium - 1` |
| Reinsurance cession ratio | `reinsurance_ceded_premium / gross_written_premium` |
| Retention ratio | `retained_premium / gross_written_premium` |
| Paid claims ratio | `paid_claims / gross_written_premium` |

If the denominator is zero or missing, the app should avoid calculation and show data as not available.

## Difference Between App Claims / Premiums Ratio And Fasecolda Technical Indicators

The app currently shows an analytical Claims / Premiums ratio, also labelled in Spanish as Siniestros / Primas. It is calculated from the available normalized app database as:

`claims / gross_written_premium`

This metric is useful for broker market intelligence because it provides a consistent, filterable view across companies, lines, cities, and years. However, it should not be interpreted as Fasecolda's official technical loss ratio, technical siniestralidad, combined ratio, incurred loss ratio, or paid loss ratio unless the source methodology is explicitly confirmed.

Fasecolda's visualizador or other official technical views may include or be affected by:

- Incurred claims.
- Paid claims.
- Claim reserves.
- Earned premiums.
- Emitted premiums.
- Retained premiums.
- Commissions.
- Administrative expenses.
- Personnel expenses.
- Other technical expenses.

Therefore, the app's Claims / Premiums ratio should not be expected to match official Fasecolda technical indicators one-to-one without confirming the exact numerator, denominator, period basis, and expense treatment. SOAT should be reviewed especially carefully because Fasecolda's technical views may include methodological components that are not captured by a simple claims/premiums ratio.

## Company Mapping

Company names can differ between Fasecolda sources. The app uses `dim_company_mapping` to align source names with standard company names. This supports comparisons between Ciudades y Ramos and Indicadores de Gestion.

Mappings are not a substitute for legal entity analysis. They are an analytical standardization layer for market intelligence.

## Line-of-Business Mapping

Line names can also differ between sources. The app uses `dim_line_of_business_mapping` to align local source names with standard lines of business. The mapping table can also identify aggregate lines through `lob_group = AGGREGATE`.

Aggregate lines such as total damages, total persons, or total social security can duplicate individual lines. Reinsurance View allows excluding aggregate lines from rankings by default.

## Data Validation

Validation scripts and reports check for:

- Missing or unexpected values.
- Non-positive premium records.
- Negative ceded premium.
- Retained premium greater than gross written premium.
- Ratios outside expected ranges.
- Paid claims ratio above expected thresholds.
- Aggregate lines and possible duplicated aggregate impact.
- Differences between extracted and recalculated ratios.

Warnings are review signals, not automatic proof that data is wrong.

## Appropriate Uses

Use the app for:

- Internal broker meeting preparation.
- Market sizing and ranking.
- Company and line-of-business exploration.
- Technical signal spotting.
- Questions for client discussions.
- Data quality review.

## Company Brief Methodology

The Company Brief is a structured broker-preparation view generated from the app's internal DuckDB data model. It uses public Fasecolda data, mapping tables and calculated app metrics to summarize market position, competitors, portfolio mix, premium evolution, Claims / Premiums movement, technical alerts and meeting questions.

It does not include external intelligence, key people, leadership context or news. Those sources will be handled separately in later AI Brief and News phases. Broker questions and alerts are discussion prompts, not underwriting conclusions.

## Reinsurance View Methodology

The Reinsurance View is a treaty-broker preparation view based on the complementary Fasecolda - Indicadores de Gestion 2025 source. It uses the app's mapping tables to align company and line names where possible, then recalculates cession, retention and paid-claims ratios at the selected aggregation level.

The module is intended to support discussion questions such as where the company cedes more premium, where it appears to retain more risk, how its selected cession ratio compares with the selected market context, and which lines may deserve a treaty conversation.

Important limitations:

- Reinsurance indicators remain exploratory and source-dependent.
- Ratios are recalculated from monetary values and should not be summed.
- Aggregate lines can duplicate individual lines and are excluded from rankings by default.
- Current available reinsurance data may be one-period heavy, so year-over-year treaty movement may not always be available.
- Signals and questions are broker prompts, not underwriting conclusions or placement advice.

## Inappropriate Uses

Do not use the app as:

- A formal actuarial model.
- A statutory reporting source.
- A legal or financial advice tool.
- A replacement for source-file validation.
- A production data pipeline.

Before using figures externally or in formal presentations, validate them against original Fasecolda files and internal review standards.
