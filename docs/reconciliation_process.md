# Formato 290 Reconciliation Process

## Purpose

Reconciliation lets a broker or data owner compare dashboard results against official reference values from SFC, Datos Abiertos or an official Power BI view.

The code does not scrape Power BI. Official values must be entered manually into the template.

## Template

The pipeline creates:

```text
data/reference/formato_290_reconciliation_template.csv
```

Columns:

- `metric_name`
- `period`
- `company`
- `ramo`
- `official_value`
- `dashboard_value`
- `difference`
- `percentage_difference`
- `tolerance_absolute`
- `tolerance_percentage`
- `status`
- `comments`

## Running reconciliation

Populate the official values, then run:

```powershell
cd "C:\Users\PC\Documents\colombia_insurance_market_dashboard - copia"
python scripts\reconcile_formato_290.py
```

Output:

```text
outputs/reconciliation/formato_290_reconciliation_report.csv
```

## Interpretation

- `PASS`: difference is within configured tolerance.
- `WARNING`: comparison could not be fully evaluated.
- `FAIL`: difference exceeds tolerance.

Differences should be reviewed before promoting any Formato 290 metric for formal client or market use.

