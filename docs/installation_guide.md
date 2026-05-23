# Installation Guide - Colombia MVP Demo

## Purpose

This guide explains how to run the Colombia MVP demo locally. The demo branch includes a static DuckDB snapshot for Streamlit Cloud testing.

## Requirements

- Python 3.11.
- Git, if cloning from GitHub.
- Access to the private repository.
- No API keys are required for the core dashboard.

## Local Setup

```powershell
cd "C:\Users\PC\Documents\colombia_insurance_market_dashboard - copia"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app\streamlit_app.py
```

## Expected Demo Files

The demo branch should include:

- `app/streamlit_app.py`
- `src/`
- `docs/`
- `.streamlit/config.toml`
- `requirements.txt`
- `runtime.txt`
- `data/mappings/`
- `data/database/insurance_market.duckdb`

The demo branch should not include:

- `data/raw/`
- `data/processed/`
- `outputs/`
- `.venv/`
- `.env`
- `.streamlit/secrets.toml`

## Streamlit Cloud

Use:

- Branch: `demo-streamlit-cloud`
- Main file path: `app/streamlit_app.py`

After deployment, reboot the app and test filters, Data Status, Reports / Export, and Reinsurance View.

## Current Limitation

This demo uses a static database snapshot. It does not yet download or refresh data automatically from Fasecolda.
