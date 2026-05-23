# Data Dictionary - Colombia MVP

This dictionary explains the business meaning, source, unit, and use of the main fields in the Colombia MVP. It is written for reinsurance brokers and internal reviewers who need to understand where numbers come from before using them in meetings.

## Core Market Fields

| Field name | Business meaning | Source | Unit | Calculation / transformation | Used in app modules | Notes / limitations |
|---|---|---|---|---|---|---|
| `country` | Country module represented by the record. | App data model | Text | Standardized during loading. | All modules | Current demo is Colombia only. |
| `source` | Public data source that produced the record. | Fasecolda / load process | Text | Assigned during loading. | Data Status, traceability, all analytics | Core source is Fasecolda - Ciudades y Ramos. |
| `year` | Reporting year. | Derived from source period date | Calendar year | Extracted from `period_date`. | Filters, trends, growth, reports | Year alone does not identify whether a source file is full-year or YTD. |
| `month` | Reporting cut-off month. | Derived from source period date | Calendar month | Extracted from `period_date`. | Methodology, snapshot selection | Ciudades y Ramos monthly files are treated as cumulative cuts. |
| `period_date` | Reporting period end date. | Source workbook period / load process | Date | Converted to date during loading. | Data Status, traceability | Used to identify latest available period. |
| `company_local` | Company name as it appears in the source. | Fasecolda | Text | Extracted from source. | Traceability | May differ across sources or over time. |
| `company_standard` | Standard company name used in the app. | Mapping / standardization | Text | Normalized from source company names. | Filters, rankings, company brief | Not a legal entity hierarchy. Broker review may be needed for groups. |
| `company_name_norm` | Normalized comparison key for company names. | Mapping logic | Text | Uppercase, trimmed, accents removed where needed. | Mapping support | Used for matching, not usually shown to users. |
| `line_of_business_local` | Line of business name as it appears in the source. | Fasecolda | Text | Extracted from source. | Traceability | Source naming can differ from Indicadores de Gestion. |
| `line_of_business_standard` | Standard line of business used in the app. | Mapping / standardization | Text | Normalized from source line names. | Filters, rankings, technical signals | Mappings should be reviewed when adding new sources. |
| `line_of_business` | Business line label in charts or reports. | App display / standard field | Text | Usually derived from `line_of_business_standard`. | Charts, reports | Use standard label for comparisons. |
| `lob_group` | Business grouping for lines, including aggregate flags. | `dim_line_of_business_mapping` | Text | Maintained in mapping table. | Reinsurance View, aggregate exclusion | `AGGREGATE` lines can duplicate individual lines. |
| `city` | City-level market geography. | Fasecolda - Ciudades y Ramos | Text | Extracted from source. | Filters, market views | Reinsurance source does not include city-level detail. |
| `department` | Department-level geography, if available in future data. | Not currently used | Text | Not currently populated in the core app. | Future regional model | Current demo uses city, not department. |
| `gross_written_premium` | Premium volume reported by the market or company. | Fasecolda - Ciudades y Ramos; Indicadores de Gestion where available | COP | Ciudades y Ramos `VALOR` is treated as thousands of COP and converted to COP in the app. Annual analytics use the latest available monthly cut per year. | KPIs, trends, rankings, briefs, signals, exports | Do not sum multiple monthly cumulative cuts to create annual values. |
| `claims` | Claims reported in Ciudades y Ramos. | Fasecolda - Ciudades y Ramos | COP | Source `VALOR` treated as thousands of COP and converted to COP. | Loss ratio, trends, briefs | This is not the same field as paid claims in Indicadores de Gestion. |
| `loss_ratio` | Claims pressure relative to premiums. | Calculated in app | Ratio / percentage | `claims / gross_written_premium`, recalculated after aggregation. | Market Overview, Company Explorer, Line Explorer, Company Brief, Technical Signals | Ratios are never summed. Interpret with portfolio size and source limitations. |
| `market_share` | Company share of selected market premium. | Calculated in app | Ratio / percentage | Company premium divided by total premium in the selected filter scope. | Market Overview, Company Brief, Technical Signals | Changes with filters for year, company, line, and city. |
| `growth_rate` / `premium_growth` | Premium movement versus previous available year. | Calculated in app | Ratio / percentage | Current period premium divided by previous period premium minus 1. | Market Overview, Company Brief, Technical Signals | Sensitive to low premium bases, missing prior years, and classification changes. |
| `retained_premium` | Premium retained by the insurer after reinsurance. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source and aggregated as monetary value. | Reinsurance View, Company Brief reinsurance indicators, exports | Exploratory source pending deeper methodological validation. |
| `reinsurance_ceded_premium` | Premium ceded to reinsurance. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source and aggregated as monetary value. | Reinsurance View, Technical Signals, exports | Aggregate lines can duplicate individual lines if not excluded. |
| `reinsurance_cession_ratio` | Share of premium ceded to reinsurance. | Fasecolda - Indicadores de Gestion 2025 / app calculation | Ratio / percentage | `reinsurance_ceded_premium / gross_written_premium`, recalculated at selected aggregation level. | Reinsurance View, Technical Signals | Do not sum extracted ratios. Review large or negative ratios. |
| `retention_ratio` | Share of premium retained by insurer. | Fasecolda - Indicadores de Gestion 2025 / app calculation | Ratio / percentage | `retained_premium / gross_written_premium`, recalculated at selected aggregation level. | Reinsurance View | Exploratory. Validate before formal use. |
| `paid_claims` | Paid claims from Indicadores de Gestion. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source. | Reinsurance View | Different basis from `claims` in Ciudades y Ramos. |
| `record_count` | Number of records behind a view or validation summary. | App calculation | Count | Count of rows after filters or in source tables. | Data Status, KPIs, validation | Record count is traceability, not market size. |
| `source_file` | Workbook or file used to create the record. | Load process | Text | Preserved from extraction. | Data Status, traceability | Critical for reconciling numbers to source. |
| `source_sheet` | Excel sheet used to create the record, where captured. | Load process / future enhancement | Text | Not consistently populated in current core table. | Future validation | Use `source_file` as primary traceability in current demo. |
| `update_date` / `updated_at` | Date/time when data was loaded or transformed. | Load process | Timestamp | Assigned during pipeline execution where available. | Data Status | Current Streamlit Cloud demo is a static snapshot, not auto-updated. |

## Important Unit Notes

- Fasecolda - Ciudades y Ramos `VALOR` is treated as thousands of COP and converted to COP in the app analytics layer.
- App labels such as `COP MM` show millions of COP after the conversion.
- Annual analytics use the latest available monthly cut per year to avoid summing cumulative monthly files.
- Reinsurance metrics from Indicadores de Gestion are complementary and exploratory.

## Broker Interpretation

Use this data to prepare meetings, understand market position, spot technical movements, and ask better questions. Do not use it as a final actuarial, accounting, legal, or financial source without validating figures against original Fasecolda files and internal standards.
