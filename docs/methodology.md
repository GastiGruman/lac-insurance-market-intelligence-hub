# Methodology

## Current Colombia Sources

The Colombia module currently uses public Fasecolda data:

- Fasecolda - Ciudades y Ramos: core regional source for premiums, claims, companies, lines of business and cities.
- Fasecolda - Indicadores de Gestion 2025: complementary exploratory source for retained premium, ceded premium, cession ratio, retention ratio and paid claims.

## How Ciudades y Ramos Is Used

Ciudades y Ramos is the main source for the regional core table `fact_market_core`.

It supports:

- Market overview.
- Company explorer.
- Line of business explorer.
- Company brief.
- Technical signals.
- Filtered exports.

The `VALOR` field in the extracted Ciudades y Ramos files is treated as thousands of COP and converted to COP in the app analytics layer.

Monthly Ciudades y Ramos files are cumulative period cuts. For annual analytics, the app uses the latest available month in each selected year instead of summing every monthly cut. This avoids double-counting year-to-date values. Loss ratio is calculated after aggregation as claims divided by gross written premium.

## How Indicadores de Gestion Is Used

Indicadores de Gestion 2025 is loaded into `fact_indicadores_gestion_2025`.

It supports:

- Reinsurance View.
- Exploratory retained premium and ceded premium metrics.
- Exploratory cession and retention ratios.
- Company brief reinsurance indicators when mapping is available.
- Reinsurance summary export.

This source remains complementary and exploratory. It requires deeper methodology review before integration into the core regional model.

## Why Mappings Are Needed

Fasecolda sources do not always use exactly the same company and line of business names.

The platform uses:

- `dim_line_of_business_mapping`
- `dim_company_mapping`

These mapping tables connect source names to standard regional names. Reinsurance View and Company Brief use these mappings instead of hardcoded dictionaries.

## Ratio Calculations

Ratios are recalculated at the selected aggregation level:

- `loss_ratio = claims / gross_written_premium`
- `reinsurance_cession_ratio = reinsurance_ceded_premium / gross_written_premium`
- `retention_ratio = retained_premium / gross_written_premium`
- `paid_claims_ratio = paid_claims / gross_written_premium`

Ratios are not summed.

## Market Share Calculation

Market share is calculated as:

`company gross_written_premium / selected market gross_written_premium`

The selected market reference changes with filters for country, years, line of business and city.

## Aggregate Lines

Indicadores de Gestion includes aggregate lines such as:

- `TOTAL DAÑOS`
- `TOTAL PERSONAS`
- `TOTAL SEGURIDAD SOCIAL`

These can duplicate individual lines when included in rankings. Reinsurance View includes a default option to exclude aggregate lines based on `lob_group = AGGREGATE` in the line mapping table.

## YTD Versus Full-Year Periods

Partial-year data should not be compared directly against full-year data. A future 2026 YTD period, for example, should not be compared against full-year 2025 without a clear warning or an equivalent-period adjustment.

## Broker Use

The platform is designed for meeting preparation and market intelligence. Outputs are not legal, actuarial or financial advice. Broker interpretation should cite source, period, metric and methodology when used with clients.
