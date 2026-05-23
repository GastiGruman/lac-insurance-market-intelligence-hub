# Source-to-Module Traceability Matrix

This matrix explains which data source supports each app module and how much confidence users should place in the output during internal testing.

| App module | Primary source | Secondary source | Main fields used | Calculation performed | Known limitations | Confidence level |
|---|---|---|---|---|---|---|
| Market Overview | Fasecolda - Ciudades y Ramos | None | `gross_written_premium`, `claims`, `year`, `company_standard`, `line_of_business_standard`, `city` | Premium totals, claims totals, analytical Claims / Premiums ratio, market share, premium growth | Uses static demo snapshot; annual views use latest cut per year; Claims / Premiums is not official technical siniestralidad or combined ratio | High for internal market intelligence |
| Company Explorer | Fasecolda - Ciudades y Ramos | None | Company, premiums, claims, year, line | Company premium trend, claims trend, Claims / Premiums ratio, top lines | Depends on selected filters and standard company naming; Claims / Premiums is not official technical siniestralidad | High for internal market intelligence |
| Line of Business Explorer | Fasecolda - Ciudades y Ramos | None | Line, company, premiums, claims, year | Line trend, company ranking, Claims / Premiums by company | Source line definitions should be reviewed for formal use; SOAT may differ materially from official technical indicators | High for internal market intelligence |
| Company Brief | Fasecolda - Ciudades y Ramos | Indicadores de Gestion 2025 where mapped | Company, line, premium, claims, market premium, competitors, portfolio mix, reinsurance fields | Broker-ready executive snapshot, market position, competitors, portfolio mix, premium and Claims / Premiums evolution, technical alerts, reinsurance preview, meeting questions | Reinsurance indicators are exploratory and depend on mapping availability; external intelligence, leadership and news are handled in later AI/news phases | Medium |
| Technical Signals | Fasecolda - Ciudades y Ramos | Indicadores de Gestion 2025 | Premiums, claims, growth, market share, cession ratio | Growth rankings, Claims / Premiums pressure, market share movement, cession ratio watchlist | Automated signals require broker interpretation; Claims / Premiums is not official combined ratio or technical loss ratio | Medium |
| Reinsurance View | Fasecolda - Indicadores de Gestion 2025 | Mapping tables | Gross premium, retained premium, ceded premium, paid claims, line, company | Cession ratio, retention ratio, paid claims ratio, rankings | Complementary exploratory source; aggregate lines can duplicate individual lines | Exploratory |
| Data Status | DuckDB metadata and validation files | Mapping tables and Phase 3 pipeline metadata | Source, dates, records, source files, mappings, validation outputs, pipeline status | Coverage summaries, mapping counts, validation warning counts, latest pipeline run status | Validation files may not exist in Streamlit Cloud unless generated; pipeline is manual-run only | High for transparency, Medium for validation completeness |
| Reports / Export | Current filtered app data | Indicadores de Gestion 2025 for reinsurance export | Same as selected module/filter | CSV exports, markdown/HTML brief exports | Exports reflect current demo snapshot and filters | Medium |
| Data Table | Fasecolda - Ciudades y Ramos | None | Filtered rows from core market table | Shows first 1,000 filtered records | Not intended as full raw-data delivery | High for traceability sample |
| AI Brief placeholder | Structured app data if configured | Optional LLM provider | Current filters and calculated summaries | Controlled brief generation only if configured | AI is not part of Phase 2; no key means placeholder only | Placeholder |
| News placeholder | Optional search/news provider if configured | Optional AI summary if configured | News provider results | Source-based summaries only if configured | News is not part of Phase 2; no provider means placeholder only | Placeholder |

## Confidence Level Definitions

- **High**: suitable for internal broker market intelligence, with source and methodology caveats.
- **Medium**: useful for discussion and preparation, but requires additional review before external use.
- **Exploratory**: early analytical view that should be validated before being used as a formal basis.
- **Placeholder**: interface exists, but the feature is not active unless providers are configured.
