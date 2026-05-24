# Release Checklist

Use this checklist before pushing changes to the demo branch or rebooting Streamlit Cloud.

## Before Commit

- `git status` shows only intended code/docs/demo files.
- No `data/raw/` files are staged.
- No `data/processed/` files are staged.
- No `data/metadata/` files are staged.
- No candidate database is staged.
- No database backup is staged.
- No `.venv/` files are staged.
- No `.env` file is staged.
- No `.streamlit/secrets.toml` file is staged.
- No `outputs/` files are staged.
- No local logs or temporary files are staged.
- `python -m py_compile app/streamlit_app.py` passes.
- `src/` Python compile check passes.
- Local Streamlit app returns HTTP 200.
- Smoke test passes.

## Before Streamlit Cloud Reboot

- Push completed successfully.
- Correct branch is selected: `demo-streamlit-cloud`.
- Main file path remains `app/streamlit_app.py`.
- Stable demo database was not changed unless intentionally approved.
- Candidate database was not committed.
- Documentation notes are updated for user-facing methodology or operational changes.

## After Streamlit Cloud Reboot

- App opens in Chrome.
- Browser refresh does not crash the app.
- App opens in Edge or another browser.
- Market Overview works.
- Company Brief works.
- AI Brief works.
- News works.
- Reinsurance View works.
- Reports / Export works.
- Data Status works.
- Data Table works.
- Empty year selection shows a friendly warning.
- CSV export works.
- Excel export works if runtime support is available.

## Release Decision

Release is acceptable only when the app remains stable and no prohibited files are included.

