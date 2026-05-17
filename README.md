# Colombia Insurance Market Intelligence

MVP inicial de una plataforma interna de inteligencia de mercado asegurador para Colombia, usando información pública de Fasecolda.

## Objetivo del proyecto

Consolidar información pública del mercado asegurador colombiano para visualizar primas, siniestros, siniestralidad, crecimiento y participación de mercado por compañía, ramo, ciudad y año.

La finalidad del proyecto es apoyar a brokers en la preparación de reuniones, análisis de mercado, identificación de tendencias técnicas y generación de insights comerciales.

## Fuente de información

- Fasecolda
- Información pública de primas y siniestros
- Periodo inicial: 2015-2024

## Estructura del proyecto

```text
colombia_insurance_market_dashboard/
│
├── app/
│   └── streamlit_app.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── database/
│
├── docs/
├── notebooks/
├── outputs/
├── src/
│   ├── test_read_files.py
│   ├── combine_fasecolda_files.py
│   ├── clean_fasecolda_data.py
│   └── load_to_duckdb.py
│
├── requirements.txt
└── README.md
```

## UI theme and branding

The Streamlit UI uses a professional internal-market-intelligence theme configured in:

```text
.streamlit/config.toml
```

Reusable UI helpers live in:

```text
src/ui_components.py
```

Current visual direction:

- Deep navy and blue accents.
- White content background.
- Light grey secondary panels.
- Clean KPI cards.
- Executive-style header without a company logo.
- Professional broker-focused wording.

An `assets/` folder exists for future static assets. No logo is currently used. If a corporate-approved logo is added later, place it in `assets/` and update the header helper in `src/ui_components.py` carefully so the app still falls back to text if the image is missing.

Theme colors can be adjusted in both:

- `.streamlit/config.toml`
- `src/ui_components.py`
