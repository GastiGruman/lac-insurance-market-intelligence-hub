# Maintenance Runbook

## Purpose

This runbook explains how to operate the Colombia MVP safely while it remains a Streamlit Cloud demo with a static DuckDB snapshot and a manual Fasecolda ingestion pipeline.

Use this document before refreshing data, comparing a candidate database, promoting a database, or rebooting the Streamlit Cloud demo.

## Current Operating Model

- Environment: Streamlit Cloud demo.
- App branch: `demo-streamlit-cloud`.
- Main app file: `app/streamlit_app.py`.
- Stable demo database: `data/database/insurance_market.duckdb`.
- Pipeline mode: manual controlled run.
- Scheduled automation: not enabled.
- Candidate promotion: manual approval only.

## Routine Update Workflow

1. Pull the latest code.

```powershell
git pull
```

2. Activate the local environment.

```powershell
.venv\Scripts\activate
```

3. Run source discovery.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode discover
```

4. Download new source files if direct files are available.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode download
```

5. Process available local source files.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode process
```

6. Validate pipeline outputs.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode validate
```

7. Build or refresh the candidate database without promotion.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode update-db
```

8. Compare candidate database against the current stable demo database.

```powershell
python -m src.pipeline.compare_candidate_database
```

9. Review:

- `docs/candidate_database_review.md`
- local comparison files under `data/metadata/db_comparison/`
- local pipeline status under `data/metadata/`

10. Decide whether promotion is appropriate.

Promotion is not automatic. It requires a clean review, app compatibility checks, and explicit approval from the business owner or data owner.

11. If promotion is approved in a future maintenance cycle, run the explicit promotion command.

```powershell
python -m src.pipeline.run_colombia_pipeline --mode update-db --promote
```

12. Test locally after any promoted database change.

```powershell
python -m streamlit run app\streamlit_app.py
```

13. Commit and push only safe files.

Do not commit raw files, processed files, pipeline metadata, candidate databases, backups, secrets, virtual environments, logs, or outputs.

14. Reboot Streamlit Cloud.

Use the Streamlit Cloud interface after the reviewed branch is pushed.

15. Run the final smoke test.

## Smoke Test Checklist

Run these checks locally and again after any Streamlit Cloud reboot:

- Fresh app open.
- Browser refresh.
- Market Overview.
- Company Brief.
- AI Brief.
- News.
- Reinsurance View.
- Reports / Export.
- Data Status.
- Data Table.
- Empty year selection.
- Company: `BOLIVAR`.
- Company: `BOLIVAR` and line: `INCENDIO Y LUCRO CESANTE`.
- Line: `SOAT`.
- CSV export.
- Excel export if runtime support is available.

Expected result: no app-level crash. Empty selections or unavailable data should show friendly warnings.

## Promotion Rules

Promotion may be considered only when:

- Candidate database exists and opens successfully.
- Required app tables exist.
- Required app columns exist.
- Year and period coverage is expected.
- Candidate row counts and totals are explainable.
- No app-breaking schema change is present.
- Candidate comparison recommends promotion.
- Local app smoke test passes with the candidate database.
- Business/data owner explicitly approves.

Promotion should be blocked when:

- Required app table or column is missing.
- Candidate database cannot be opened.
- A major year, company, line of business, or source disappears without explanation.
- Premium or claims totals are materially inconsistent without explanation.
- Validation reports contain blocking errors.
- The app fails against the candidate database.
- Approval has not been given.

## Files That Should Never Be Committed

- `data/raw/`
- `data/processed/`
- `data/metadata/`
- `data/database/insurance_market_candidate.duckdb`
- `data/database/backups/`
- `outputs/`
- `.venv/`
- `.env`
- `.streamlit/secrets.toml`
- local logs or temporary files.

The only database intentionally included in the demo branch is the stable Streamlit Cloud snapshot:

- `data/database/insurance_market.duckdb`

## Rollback Plan

### Bad Code Change

If a bad code change is pushed, revert the Git commit or return the Streamlit Cloud app to the prior stable commit/branch.

```powershell
git log --oneline
git revert <commit_sha>
git push
```

### Bad Database Promotion

If a database is promoted in a future cycle and proves faulty:

1. Stop using the faulty database.
2. Restore the prior file from `data/database/backups/` if available.
3. Run local smoke tests.
4. Commit only the intentionally restored stable database if it is required for Streamlit Cloud.
5. Reboot Streamlit Cloud and repeat the smoke test.

### Demo Stability Principle

When in doubt, keep the existing stable demo database and do not promote a candidate.

