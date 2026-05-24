# Operational Status

## Current Environment

- Environment: Streamlit Cloud demo.
- Branch: `demo-streamlit-cloud`.
- App entrypoint: `app/streamlit_app.py`.
- Database: `data/database/insurance_market.duckdb`.
- Data mode: static demo snapshot.

## Current Automation Status

- Pipeline mode: manual controlled.
- Scheduled automation: not enabled.
- Candidate database promotion: manual approval only.
- Live news: not enabled.
- External AI: not enabled.
- Secrets required to run app: none.

## Data Refresh Position

The project includes a manual Fasecolda ingestion pipeline and a candidate database comparison workflow. The current Streamlit Cloud app does not run ingestion automatically and does not promote candidate databases without explicit approval.

## Operational Readiness

Ready for:

- Limited internal broker testing.
- Controlled manual data refresh trials.
- Candidate database review.
- IT/Data handoff discussion.

Not ready for:

- Unattended scheduled data refresh.
- Production corporate hosting.
- External client use without data review.
- Automated live AI or live news operations.

## Recommended Next Operational Step

Run one controlled monthly update cycle using `docs/maintenance_runbook.md`, then review with IT/Data whether the process should move to an internal server, VM, or managed cloud scheduler.

