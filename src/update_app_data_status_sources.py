from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_before_data_status_sources.py")

text = APP_FILE.read_text(encoding="utf-8")
BACKUP_FILE.write_text(text, encoding="utf-8")

print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# Agregar bloque de fuentes complementarias en Data Status
# ============================================================

old_block = '''    st.markdown("### Fuentes de datos")

    source_summary = (
        country_df
        .groupby(["country", "regulator", "source"], as_index=False)
        .agg(
            records=("metric_value", "count"),
            files=("source_file", "nunique"),
            first_date=("period_date", "min"),
            last_date=("period_date", "max")
        )
    )

    st.dataframe(source_summary, use_container_width=True)
'''

new_block = '''    st.markdown("### Fuentes de datos")

    source_summary = (
        country_df
        .groupby(["country", "regulator", "source"], as_index=False)
        .agg(
            records=("metric_value", "count"),
            files=("source_file", "nunique"),
            first_date=("period_date", "min"),
            last_date=("period_date", "max")
        )
    )

    source_summary["status"] = "Core regional principal"
    source_summary["usage"] = "Primas, siniestros, siniestralidad, compañías, ramos, ciudades"

    # Agregar fuente complementaria de Indicadores de Gestión si está cargada
    if "indicadores_df" in globals() and not indicadores_df.empty:
        indicadores_country_df = indicadores_df[indicadores_df["country"] == selected_country].copy()

        if not indicadores_country_df.empty:
            indicadores_country_df["period_date"] = pd.to_datetime(
                indicadores_country_df["period_date"],
                errors="coerce"
            )

            indicadores_summary = pd.DataFrame([{
                "country": selected_country,
                "regulator": "FASECOLDA",
                "source": "FASECOLDA - INDICADORES DE GESTION 2025",
                "records": len(indicadores_country_df),
                "files": indicadores_country_df["source_file"].nunique(),
                "first_date": indicadores_country_df["period_date"].min(),
                "last_date": indicadores_country_df["period_date"].max(),
                "status": "Fuente complementaria exploratoria",
                "usage": "Cesión al reaseguro, retención, siniestros pagados, ratios técnicos"
            }])

            source_summary = pd.concat(
                [source_summary, indicadores_summary],
                ignore_index=True
            )

    st.dataframe(source_summary, use_container_width=True)

    st.info(
        "La fuente principal del core regional es Fasecolda - Ciudades y Ramos. "
        "Indicadores de Gestión 2025 se está usando como fuente complementaria exploratoria "
        "para la Reinsurance View y requiere validación metodológica antes de integrarse "
        "al core regional principal."
    )
'''

if old_block not in text:
    raise ValueError(
        "No se encontró el bloque exacto de 'Fuentes de datos' en Data Status. "
        "No se modificó el archivo."
    )

text = text.replace(old_block, new_block)

APP_FILE.write_text(text, encoding="utf-8")

print("Data Status actualizado correctamente con fuentes complementarias.")
print("Ahora ejecuta: streamlit run app\\streamlit_app.py")