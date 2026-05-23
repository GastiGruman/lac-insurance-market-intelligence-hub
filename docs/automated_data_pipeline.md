# Automated Regulatory Data Pipeline

## Purpose

Phase 3 introduces the first automated regulatory ingestion pipeline for the Colombia MVP. The pipeline is designed to detect public Fasecolda source files, download new files, normalize them, validate outputs, and prepare a safe DuckDB candidate without breaking the current Streamlit Cloud demo.

The pipeline is manual-run in this phase. It is not yet a scheduled corporate job.

## Source Discovery

Configured official Fasecolda pages:

- Fasecolda - Ciudades y Ramos: `https://www.fasecolda.com/fasecolda/estadisticas-del-sector/ciudades-y-ramos/`
- Fasecolda - Indicadores de Gestion: `https://www.fasecolda.com/fasecolda/estadisticas-del-sector/indicadores-de-gestion/`

The discovery step scans those pages for direct downloadable files. If direct file discovery fails because the website structure changes, the pipeline writes a clear warning and uses a manual registry fallback with the official landing pages.

## Download Flow

The downloader:

- Downloads only direct file URLs.
- Skips landing-page-only registry entries.
- Avoids re-downloading files that already exist locally.
- Stores raw files under `data/raw/fasecolda/<source>/<period>/`.
- Writes a source manifest to `data/metadata/source_manifest.csv`.

Raw files remain excluded from Git.

## Processing Flow

Processed files are written under `data/processed/fasecolda/`.

The first version includes:

- `process_ciudades_ramos.py`: normalizes Ciudades y Ramos Excel files when local raw workbooks are available.
- `process_indicadores_gestion.py`: creates an auditable normalized continuity extract from the current DuckDB `fact_indicadores_gestion_2025` table. The source-file-specific parser can be expanded in a later iteration.

Normalized outputs preserve:

- Source.
- Period.
- Company.
- Line of business.
- Mapping results.
- Source file and sheet.
- Metric fields where available.

Unavailable metrics are kept as nulls rather than invented.

## Mapping Integration

The pipeline uses:

- `data/mappings/company_mapping.csv`
- `data/mappings/line_of_business_mapping.csv`

It normalizes source names, applies standard names, and writes review files:

- `data/metadata/unmapped_companies.csv`
- `data/metadata/unmapped_lines_of_business.csv`

Unmapped records are not automatically rejected. They are review items for data stewardship.

## Validation Flow

The validation layer checks:

- Required columns.
- Valid period dates.
- Valid year and month values.
- Null key fields.
- Negative premium and claims values.
- Ratio sanity bounds.
- Duplicate audit keys.
- Current DuckDB table availability.

Outputs:

- `data/metadata/pipeline_validation_report.csv`
- `data/metadata/pipeline_validation_report.json`
- `data/metadata/latest_pipeline_status.md`
- `data/metadata/latest_pipeline_status.json`

Results are classified as:

- `PASS`
- `WARNING`
- `ERROR`

Warnings are review signals. Errors block database promotion.

## DuckDB Candidate and Promotion Strategy

The pipeline never overwrites the working demo database directly.

The safe strategy is:

1. Copy the current database into `data/database/insurance_market_candidate.duckdb`.
2. Load pipeline audit tables into the candidate.
3. Validate pipeline outputs and the current app tables.
4. Promote only if explicitly requested with `--promote` and validation has no errors.
5. Before promotion, create a timestamped backup in `data/database/backups/`.

Candidate databases and backups are excluded from Git.

## Candidate Database Review

Phase 3B adds a controlled review step before any database promotion:

```powershell
python -m src.pipeline.compare_candidate_database
```

The comparison writes local reconciliation files under `data/metadata/db_comparison/` and a review note at `docs/candidate_database_review.md`.

The review checks:

- Required app tables and columns.
- Row counts and schema compatibility.
- Year and period coverage.
- Premium, claims, and Claims / Premiums totals by year.
- Source, company, and line-of-business comparisons.
- SOAT, BOLIVAR, and BOLIVAR + INCENDIO Y LUCRO CESANTE slices.
- Reinsurance indicator availability.

Promotion should not proceed unless the review recommendation is `Promote now` and the user explicitly approves.

## Local Candidate App Testing

The app uses the stable demo database by default. To test the candidate locally without replacing the current database:

```powershell
$env:USE_CANDIDATE_DB="true"
python -m streamlit run app\streamlit_app.py
```

To return to the stable database:

```powershell
Remove-Item Env:\USE_CANDIDATE_DB
python -m streamlit run app\streamlit_app.py
```

Streamlit Cloud remains on the stable database by default because `USE_CANDIDATE_DB` is not set.

## How To Run

From the project root:

```powershell
python -m src.pipeline.run_colombia_pipeline --mode discover
python -m src.pipeline.run_colombia_pipeline --mode download
python -m src.pipeline.run_colombia_pipeline --mode process
python -m src.pipeline.run_colombia_pipeline --mode validate
python -m src.pipeline.run_colombia_pipeline --mode update-db
python -m src.pipeline.run_colombia_pipeline --mode full
```

To allow database promotion after review:

```powershell
python -m src.pipeline.run_colombia_pipeline --mode update-db --promote
```

Use promotion only after reviewing validation outputs.

## Generated Files

Generated local files may include:

- `data/raw/fasecolda/...`
- `data/processed/fasecolda/...`
- `data/metadata/discovered_sources.csv`
- `data/metadata/source_manifest.csv`
- `data/metadata/pipeline_validation_report.csv`
- `data/metadata/latest_pipeline_status.json`
- `data/database/insurance_market_candidate.duckdb`
- `data/database/backups/...`

Raw, processed, candidate database, backups, outputs, secrets, and virtual environments must not be committed.

## App Integration

The Streamlit app does not run the pipeline automatically. Data Status reads `data/metadata/latest_pipeline_status.json` if it exists and shows:

- Last pipeline run.
- Mode.
- Discovery status.
- Files downloaded.
- Rows processed.
- Validation status.
- Database status.
- Automation mode.

## Limitations

- Source discovery depends on Fasecolda page structure.
- Download requires direct downloadable file URLs.
- Indicadores de Gestion parsing remains partially source-specific and is treated as exploratory.
- The app's current Claims / Premiums ratio is an analytical `claims / gross_written_premium` metric and should not be treated as an official technical loss ratio or combined ratio without confirmed source methodology.
- The current phase is manual-run only.
- Scheduling should be implemented later in a controlled corporate environment.
