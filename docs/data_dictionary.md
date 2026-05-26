# Data Dictionary - Colombia MVP

This dictionary explains the business meaning, source, unit, and use of the main fields in the Colombia MVP. It is written for reinsurance brokers and internal reviewers who need to understand where numbers come from before using them in meetings.

## Core Market Fields

### Formato 290 migration note

The target Colombia source of truth is now SFC Formato 290 from Datos Abiertos Colombia dataset `e967-4a8r`. The current app can still fall back to the legacy Fasecolda snapshot if the Formato 290 tables are not present. Once `python scripts/update_formato_290.py` runs successfully, Formato 290 tables such as `clean_formato_290`, `mart_formato_290_dashboard_metrics`, and `fact_market_core_formato_290` are available in DuckDB.

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
| `gross_written_premium` | Compatibility premium metric used by the current dashboard for scale, rankings and market share. | SFC Formato 290 when available | COP | Formato 290 written premium = direct written premium + accepted co-insurance premium + accepted reinsurance premium. | KPIs, trends, rankings, briefs, signals, exports | Label as written premium, not generic premium. Period basis requires business confirmation before annualized growth. |
| `claims` | Compatibility claims metric used by the current dashboard. | SFC Formato 290 when available | COP | Formato 290 Unidad de Captura 8 / Subcuenta 999, `SINIESTROS CTA CIA`, treated as incurred claims / technical account movement. | Technical claims ratio, trends, briefs | Can be negative because it may include reserve, recovery or net technical movements. Not ordinary paid claims. |
| `loss_ratio` | Analytical technical claims ratio. Display label: Incurred Claims / Written Premium. | Calculated in app from the normalized DuckDB data model | Ratio / percentage | `claims / gross_written_premium`, recalculated after aggregation from totals. | Market Overview, Company Explorer, Line Explorer, Company Brief, Technical Signals | Not safe to call ordinary siniestralidad without qualification. It is not necessarily equal to official technical loss ratio, combined ratio, incurred loss ratio, paid loss ratio, or Fasecolda visualizer indicators. |
| `market_share` | Company share of selected market premium. | Calculated in app | Ratio / percentage | Company premium divided by total premium in the selected filter scope. | Market Overview, Company Brief, Technical Signals | Changes with filters for year, company, line, and city. |
| `growth_rate` / `premium_growth` | Premium movement versus previous available year. | Calculated in app | Ratio / percentage | Current period premium divided by previous period premium minus 1. | Market Overview, Company Brief, Technical Signals | Sensitive to low premium bases, missing prior years, and classification changes. |
| `retained_premium` | Premium retained by the insurer after reinsurance. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source and aggregated as monetary value. | Reinsurance View, Company Brief reinsurance indicators, exports | Exploratory source pending deeper methodological validation. |
| `reinsurance_ceded_premium` | Premium ceded to reinsurance. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source and aggregated as monetary value. | Reinsurance View, Technical Signals, exports | Aggregate lines can duplicate individual lines if not excluded. |
| `reinsurance_cession_ratio` | Share of premium ceded to reinsurance. | Fasecolda - Indicadores de Gestion 2025 / app calculation | Ratio / percentage | `reinsurance_ceded_premium / gross_written_premium`, recalculated at selected aggregation level. | Reinsurance View, Technical Signals | Treaty-broker discussion metric. Do not sum extracted ratios. Review large or negative ratios. Exploratory until source methodology is fully validated. |
| `retention_ratio` | Share of premium retained by insurer. | Fasecolda - Indicadores de Gestion 2025 / app calculation | Ratio / percentage | `retained_premium / gross_written_premium`, recalculated at selected aggregation level. | Reinsurance View | Treaty-broker discussion metric. Exploratory and source-dependent; validate before formal use. |
| `paid_claims` | Paid claims from Indicadores de Gestion. | Fasecolda - Indicadores de Gestion 2025 | COP | Extracted from complementary source. | Reinsurance View | Different basis from `claims` in Ciudades y Ramos. Used as a discussion signal, not a final treaty pricing view. |
| `record_count` | Number of records behind a view or validation summary. | App calculation | Count | Count of rows after filters or in source tables. | Data Status, KPIs, validation | Record count is traceability, not market size. |
| `source_file` | Workbook or file used to create the record. | Load process | Text | Preserved from extraction. | Data Status, traceability | Critical for reconciling numbers to source. |
| `source_sheet` | Excel sheet used to create the record, where captured. | Load process / future enhancement | Text | Not consistently populated in current core table. | Future validation | Use `source_file` as primary traceability in current demo. |
| `update_date` / `updated_at` | Date/time when data was loaded or transformed. | Load process | Timestamp | Assigned during pipeline execution where available. | Data Status | Current Streamlit Cloud demo is a static snapshot, not auto-updated. |

## Formato 290 Fields

| Field name | Business meaning | Source | Unit | Calculation / transformation | Used in app modules | Notes / limitations |
|---|---|---|---|---|---|---|
| `raw_formato_290` | Raw API records from Datos Abiertos. | SFC Formato 290 `e967-4a8r` | Source fields | Downloaded with Socrata pagination and ingestion metadata. | Audit and traceability | Raw table is not used directly for dashboard metrics. |
| `clean_formato_290.period_date` | Reporting period detected from `Año` and `Mes`. | Formato 290 | Date | First day of reporting month. | Data Status, marts | Period basis must be confirmed before annualization. |
| `clean_formato_290.company_name_raw` | Insurer/entity name as reported by SFC. | Formato 290 | Text | From `nombre_entidad`. | Traceability | Preserves source wording, codes and quotes where present. |
| `clean_formato_290.company_name_clean` | Clean insurer name. | Formato 290 / app transformation | Text | Removes leading entity code, unnecessary quotes and extra spaces. | Charts and analysis labels | Keeps the code separately in `company_code`. |
| `clean_formato_290.company_display_name` | Business display name. | Formato 290 / app transformation | Text | `company_code | company_name_clean`. | Filters and tables | Keeps reconciliation code visible without cluttering chart labels. |
| `clean_formato_290.ramo_name_raw` | Insurance line source column. | Formato 290 | Text | Wide ramo columns are melted into long form. | Traceability | Source field preserved. |
| `clean_formato_290.ramo_name_clean` | Clean insurance line name. | Formato 290 / app transformation | Text | Replaces underscores, removes trailing `_mes` / `MES`, uppercases. | Line analysis after migration | Includes `TOTAL` and subtotal columns that may need exclusion from rankings. |
| `clean_formato_290.concept_name` | Official unit/subaccount concept. | Formato 290 | Text | `nombre_unidad_de_captura` + `nombre_subcuenta`. | Mapping, methodology | Business review required for final metric mapping. |
| `clean_formato_290.metric_name` | Candidate app metric mapped from concept text. | App mapping rules | Text | Keyword-based transparent mapping. | Marts, Data Status | Unmatched concepts remain `pending_mapping`. |
| `clean_formato_290.normalized_value` | Numeric source value. | Formato 290 | COP, COP MM, or units depending on unit capture | Parsed from source ramo column. | Marts and validation | Unidad de Captura 19 is reported in millions of pesos; Unidad 20 in units. |
| `mart_formato_290_dashboard_metrics.metric_value` | Aggregated metric by period, company, ramo and mapped concept. | Clean Formato 290 table | COP unless unit says otherwise | Sum of normalized values for mapped concepts. | Future core dashboard metrics | Do not mix written, earned, retained and ceded premium bases. |
| `fact_market_core_formato_290` | Compatibility table for Streamlit core metrics. | Formato 290 marts | COP | Uses mapped `gross_written_premium` and preferred claims metric where available. | Market Overview, Company Explorer, Line Explorer | Created only when mapping is available. Data Status shows validation state. |

## Important Unit Notes

- Fasecolda - Ciudades y Ramos `VALOR` is treated as thousands of COP and converted to COP in the app analytics layer.
- App labels such as `COP MM` show millions of COP after the conversion.
- Annual analytics use the latest available monthly cut per year to avoid summing cumulative monthly files.
- Reinsurance metrics from Indicadores de Gestion are complementary and exploratory.
- The app field `loss_ratio` is displayed as Incurred Claims / Written Premium. It is an analytical technical movement ratio, not an official siniestralidad or combined ratio unless explicitly reconciled.

## Broker Interpretation

Use this data to prepare meetings, understand market position, spot technical movements, and ask better questions. Do not use it as a final actuarial, accounting, legal, or financial source without validating figures against original Fasecolda files and internal standards.
