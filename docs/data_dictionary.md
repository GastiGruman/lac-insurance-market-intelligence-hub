# Data Dictionary

This dictionary describes the current Colombia module fields used in the LAC Insurance Market Intelligence Hub.

## Core Fields

### `gross_written_premium`
- Source: Fasecolda - Ciudades y Ramos; Fasecolda - Indicadores de Gestion 2025 where available.
- Unit: monetary amount.
- Currency: COP.
- Calculation: for Ciudades y Ramos, extracted `VALOR` is treated as thousands of COP and converted to COP in the app analytics layer. Annual views use the latest available monthly cut per year because source files are cumulative period cuts.
- Limitations: 2026 YTD, if loaded in future, should not be compared directly with full-year periods. Do not sum multiple monthly cumulative cuts to create an annual value.

### `claims`
- Source: Fasecolda - Ciudades y Ramos.
- Unit: monetary amount.
- Currency: COP.
- Calculation: for Ciudades y Ramos, extracted `VALOR` is treated as thousands of COP and converted to COP in the app analytics layer. Annual views use the latest available monthly cut per year because source files are cumulative period cuts.
- Limitations: claims basis follows the source and may differ from paid claims in Indicadores de Gestion. Do not sum multiple monthly cumulative cuts to create an annual value.

### `loss_ratio`
- Source: calculated from Fasecolda - Ciudades y Ramos.
- Unit: ratio.
- Currency: not applicable.
- Calculation: `claims / gross_written_premium`.
- Limitations: must be recalculated after aggregation; do not sum ratios.

### `retained_premium`
- Source: Fasecolda - Indicadores de Gestion 2025.
- Unit: monetary amount.
- Currency: COP.
- Calculation: extracted retained premium value.
- Limitations: exploratory source pending deeper methodology review.

### `reinsurance_ceded_premium`
- Source: Fasecolda - Indicadores de Gestion 2025.
- Unit: monetary amount.
- Currency: COP.
- Calculation: extracted ceded premium value.
- Limitations: exploratory source; aggregate lines may duplicate individual lines.

### `reinsurance_cession_ratio`
- Source: Fasecolda - Indicadores de Gestion 2025; recalculated in app for aggregate views.
- Unit: ratio.
- Currency: not applicable.
- Calculation: `reinsurance_ceded_premium / gross_written_premium`.
- Limitations: must be recalculated after aggregation; extracted ratios are validated against calculated ratios.

### `retention_ratio`
- Source: Fasecolda - Indicadores de Gestion 2025; recalculated in app for aggregate views.
- Unit: ratio.
- Currency: not applicable.
- Calculation: `retained_premium / gross_written_premium`.
- Limitations: must be recalculated after aggregation; exploratory pending methodology review.

### `paid_claims`
- Source: Fasecolda - Indicadores de Gestion 2025.
- Unit: monetary amount.
- Currency: COP.
- Calculation: extracted paid claims value.
- Limitations: not the same field as `claims` from Ciudades y Ramos.

### `market_share`
- Source: calculated from selected filtered market data.
- Unit: ratio.
- Currency: not applicable.
- Calculation: company premium divided by total premium in the selected market reference.
- Limitations: changes with filters for country, year, company, line and city.

### `premium_growth`
- Source: calculated from selected filtered market data.
- Unit: ratio.
- Currency: not applicable.
- Calculation: current period premium divided by previous available period premium minus 1.
- Limitations: sensitive to partial-year periods, missing prior years and changes in source classification.

### `source_file`
- Source: load pipeline metadata.
- Unit: text.
- Currency: not applicable.
- Calculation: source workbook or file name from which the record was extracted.
- Limitations: should be preserved for traceability.

### `period_date`
- Source: load pipeline metadata from source file period.
- Unit: date.
- Currency: not applicable.
- Calculation: period-end date assigned during extraction.
- Limitations: period-end dates should be checked before comparing YTD with full-year periods.

### `year`
- Source: derived from `period_date` or source file period.
- Unit: calendar year.
- Currency: not applicable.
- Calculation: year component of the reporting period.
- Limitations: year alone does not distinguish YTD from full-year.

### `month`
- Source: derived from `period_date` or source file period.
- Unit: calendar month.
- Currency: not applicable.
- Calculation: month component of the reporting period.
- Limitations: for cumulative source files, month identifies the cut-off month. Annual analytics should use the latest available month in the year.

## Methodology Reminder

Ratios are recalculated at the selected aggregation level. Monetary metrics can be summed. Aggregate lines in Indicadores de Gestion 2025 are exploratory and may duplicate individual lines.
