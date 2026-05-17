from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_before_reinsurance.py")

app_text = APP_FILE.read_text(encoding="utf-8")

# Crear backup
BACKUP_FILE.write_text(app_text, encoding="utf-8")
print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Agregar funciones de carga
# ============================================================

load_functions_insert = '''

@st.cache_data
def load_indicadores_gestion_2025():
    try:
        conn = duckdb.connect(str(DB_PATH))
        df = conn.execute("""
            SELECT *
            FROM fact_indicadores_gestion_2025
        """).fetchdf()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_indicadores_gestion_validation():
    validation_path = Path("outputs/indicadores_gestion_2025_validation_report.csv")
    if validation_path.exists():
        return pd.read_csv(validation_path)
    return pd.DataFrame(columns=["test_name", "result", "detail"])
'''

marker = '''@st.cache_data
def load_validation_report():
    if VALIDATION_REPORT_PATH.exists():
        return pd.read_csv(VALIDATION_REPORT_PATH)
    return pd.DataFrame(columns=["test_name", "result", "detail"])
'''

if "def load_indicadores_gestion_2025" not in app_text:
    app_text = app_text.replace(marker, marker + load_functions_insert)
    print("Funciones de carga de Indicadores de Gestión agregadas.")
else:
    print("Funciones de Indicadores de Gestión ya existían. No se duplicaron.")

# ============================================================
# 2. Cargar dataframes nuevos
# ============================================================

old_load_block = '''df = load_market_core()
validation_df = load_validation_report()
'''

new_load_block = '''df = load_market_core()
validation_df = load_validation_report()
indicadores_df = load_indicadores_gestion_2025()
indicadores_validation_df = load_indicadores_gestion_validation()
'''

if "indicadores_df = load_indicadores_gestion_2025()" not in app_text:
    app_text = app_text.replace(old_load_block, new_load_block)
    print("Carga de indicadores_df agregada.")
else:
    print("Carga de indicadores_df ya existía. No se duplicó.")

# ============================================================
# 3. Actualizar tabs
# ============================================================

old_tabs = '''tab_market, tab_company, tab_line, tab_brief, tab_signals, tab_status, tab_reports, tab_data = st.tabs(
    [
        "Market Overview",
        "Company Explorer",
        "Line of Business Explorer",
        "Company Brief",
        "Technical Signals",
        "Data Status",
        "Reports / Export",
        "Data Table"
    ]
)
'''

new_tabs = '''tab_market, tab_company, tab_line, tab_brief, tab_signals, tab_reinsurance, tab_status, tab_reports, tab_data = st.tabs(
    [
        "Market Overview",
        "Company Explorer",
        "Line of Business Explorer",
        "Company Brief",
        "Technical Signals",
        "Reinsurance View",
        "Data Status",
        "Reports / Export",
        "Data Table"
    ]
)
'''

if "tab_reinsurance" not in app_text:
    app_text = app_text.replace(old_tabs, new_tabs)
    print("Tab Reinsurance View agregada.")
else:
    print("Tab Reinsurance View ya existía. No se duplicó.")

# ============================================================
# 4. Insertar sección Reinsurance View antes de Data Status
# ============================================================

reinsurance_section = r'''
# ============================================================
# TAB 6 — REINSURANCE VIEW
# ============================================================

with tab_reinsurance:
    st.subheader("Reinsurance View")
    st.caption(
        "Vista exploratoria basada en Fasecolda - Indicadores de Gestión 2025. "
        "Estos datos vienen de una fuente distinta a Ciudades y Ramos y deben validarse metodológicamente antes de usarse como dato final."
    )

    if indicadores_df.empty:
        st.warning(
            "No se encontró la tabla fact_indicadores_gestion_2025. "
            "Ejecuta primero `python src\\load_indicadores_gestion_to_duckdb.py`."
        )
    else:
        indicadores_df["period_date"] = pd.to_datetime(indicadores_df["period_date"], errors="coerce")
        indicadores_df["year"] = pd.to_numeric(indicadores_df["year"], errors="coerce").astype("Int64")
        indicadores_df["metric_value"] = pd.to_numeric(indicadores_df["metric_value"], errors="coerce")

        re_df = indicadores_df[indicadores_df["country"] == selected_country].copy()

        # Filtros alineados con la barra lateral
        if selected_company != "TODAS":
            re_df = re_df[re_df["company_standard"] == selected_company]

        if selected_line != "TODOS":
            re_df = re_df[re_df["line_of_business_standard"] == selected_line]

        # Indicadores de Gestión no trae ciudad; por eso no aplicamos filtro de ciudad
        if selected_city != "TODAS":
            st.info(
                "Nota: Indicadores de Gestión no contiene detalle por ciudad. "
                "La Reinsurance View no aplica el filtro de ciudad."
            )

        # Pasar a formato ancho para calcular KPIs correctamente
        group_cols_re = [
            "country",
            "year",
            "company_standard",
            "line_of_business_standard"
        ]

        re_wide = (
            re_df.pivot_table(
                index=group_cols_re,
                columns="metric_name",
                values="metric_value",
                aggfunc="sum"
            )
            .reset_index()
        )

        re_wide.columns.name = None

        expected_cols = [
            "gross_written_premium",
            "retained_premium",
            "reinsurance_ceded_premium",
            "paid_claims",
            "retention_ratio",
            "reinsurance_cession_ratio"
        ]

        for col in expected_cols:
            if col not in re_wide.columns:
                re_wide[col] = pd.NA

        # Recalcular ratios agregados, no sumar ratios
        total_gwp = re_wide["gross_written_premium"].sum()
        total_retained = re_wide["retained_premium"].sum()
        total_ceded = re_wide["reinsurance_ceded_premium"].sum()
        total_paid_claims = re_wide["paid_claims"].sum()

        retention_ratio = total_retained / total_gwp if total_gwp else None
        cession_ratio = total_ceded / total_gwp if total_gwp else None
        paid_claims_ratio = total_paid_claims / total_gwp if total_gwp else None

        col_a, col_b, col_c, col_d = st.columns(4)

        col_a.metric("Primas emitidas", format_millions(total_gwp))
        col_b.metric("Primas retenidas", format_millions(total_retained))
        col_c.metric("Prima cedida reaseguro", format_millions(total_ceded))
        col_d.metric("Ratio de cesión", format_percentage(cession_ratio))

        col_e, col_f, col_g, col_h = st.columns(4)

        col_e.metric("Ratio de retención", format_percentage(retention_ratio))
        col_f.metric("Siniestros pagados", format_millions(total_paid_claims))
        col_g.metric("Siniestros pagados / primas", format_percentage(paid_claims_ratio))
        col_h.metric("Registros fuente", f"{len(re_df):,}")

        st.divider()

        st.markdown("### Cesión al reaseguro por ramo")

        lob_summary = (
            re_wide.groupby("line_of_business_standard", as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                retained_premium=("retained_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
                paid_claims=("paid_claims", "sum"),
                companies=("company_standard", "nunique")
            )
        )

        lob_summary["cession_ratio"] = (
            lob_summary["reinsurance_ceded_premium"] / lob_summary["gross_written_premium"]
        )

        lob_summary["retention_ratio"] = (
            lob_summary["retained_premium"] / lob_summary["gross_written_premium"]
        )

        lob_summary["paid_claims_ratio"] = (
            lob_summary["paid_claims"] / lob_summary["gross_written_premium"]
        )

        lob_summary = lob_summary.sort_values("reinsurance_ceded_premium", ascending=False)

        lob_chart = lob_summary.head(20).copy()
        lob_chart["ceded_mm"] = lob_chart["reinsurance_ceded_premium"] / 1_000_000

        fig_ceded_lob = px.bar(
            lob_chart,
            x="line_of_business_standard",
            y="ceded_mm",
            title="Top 20 ramos por prima cedida al reaseguro",
            labels={
                "line_of_business_standard": "Ramo",
                "ceded_mm": "Prima cedida en millones de pesos"
            }
        )

        st.plotly_chart(fig_ceded_lob, width="stretch")

        col_1, col_2 = st.columns(2)

        with col_1:
            ratio_chart = lob_summary[
                lob_summary["gross_written_premium"] >= minimum_premium
            ].sort_values("cession_ratio", ascending=False).head(20)

            fig_cession_ratio = px.bar(
                ratio_chart,
                x="line_of_business_standard",
                y="cession_ratio",
                title="Top ramos por ratio de cesión",
                labels={
                    "line_of_business_standard": "Ramo",
                    "cession_ratio": "Ratio de cesión"
                }
            )

            fig_cession_ratio.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_cession_ratio, width="stretch")

        with col_2:
            retained_chart = lob_summary[
                lob_summary["gross_written_premium"] >= minimum_premium
            ].sort_values("retention_ratio", ascending=False).head(20)

            fig_retention_ratio = px.bar(
                retained_chart,
                x="line_of_business_standard",
                y="retention_ratio",
                title="Top ramos por ratio de retención",
                labels={
                    "line_of_business_standard": "Ramo",
                    "retention_ratio": "Ratio de retención"
                }
            )

            fig_retention_ratio.update_yaxes(tickformat=".1%")
            st.plotly_chart(fig_retention_ratio, width="stretch")

        st.markdown("### Top compañías por prima cedida")

        company_summary_re = (
            re_wide.groupby("company_standard", as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                retained_premium=("retained_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
                paid_claims=("paid_claims", "sum")
            )
        )

        company_summary_re["cession_ratio"] = (
            company_summary_re["reinsurance_ceded_premium"] / company_summary_re["gross_written_premium"]
        )

        company_summary_re["retention_ratio"] = (
            company_summary_re["retained_premium"] / company_summary_re["gross_written_premium"]
        )

        company_summary_re = company_summary_re.sort_values("reinsurance_ceded_premium", ascending=False)

        company_chart = company_summary_re.head(20).copy()
        company_chart["ceded_mm"] = company_chart["reinsurance_ceded_premium"] / 1_000_000

        fig_company_ceded = px.bar(
            company_chart,
            x="company_standard",
            y="ceded_mm",
            title="Top 20 compañías por prima cedida al reaseguro",
            labels={
                "company_standard": "Compañía",
                "ceded_mm": "Prima cedida en millones de pesos"
            }
        )

        st.plotly_chart(fig_company_ceded, width="stretch")

        st.markdown("### Tabla resumen por ramo")

        lob_display = lob_summary.copy()
        lob_display["gross_written_premium"] = lob_display["gross_written_premium"].map(format_millions)
        lob_display["retained_premium"] = lob_display["retained_premium"].map(format_millions)
        lob_display["reinsurance_ceded_premium"] = lob_display["reinsurance_ceded_premium"].map(format_millions)
        lob_display["paid_claims"] = lob_display["paid_claims"].map(format_millions)
        lob_display["cession_ratio"] = lob_display["cession_ratio"].map(format_percentage)
        lob_display["retention_ratio"] = lob_display["retention_ratio"].map(format_percentage)
        lob_display["paid_claims_ratio"] = lob_display["paid_claims_ratio"].map(format_percentage)

        st.dataframe(
            lob_display[
                [
                    "line_of_business_standard",
                    "companies",
                    "gross_written_premium",
                    "retained_premium",
                    "reinsurance_ceded_premium",
                    "cession_ratio",
                    "retention_ratio",
                    "paid_claims",
                    "paid_claims_ratio"
                ]
            ],
            width="stretch"
        )

        st.markdown("### Validación de Indicadores de Gestión 2025")

        if indicadores_validation_df.empty:
            st.warning(
                "No se encontró reporte de validación de Indicadores de Gestión. "
                "Ejecuta `python src\\validate_indicadores_gestion_2025.py`."
            )
        else:
            validation_counts_re = indicadores_validation_df["result"].value_counts().reset_index()
            validation_counts_re.columns = ["result", "count"]

            col_v1, col_v2 = st.columns([1, 2])

            with col_v1:
                st.dataframe(validation_counts_re, width="stretch")

            with col_v2:
                st.dataframe(indicadores_validation_df, width="stretch")

        st.warning(
            "Metodología: esta vista usa Fasecolda - Indicadores de Gestión 2025. "
            "Los ratios se recalculan a nivel agregado y no se suman. "
            "La fuente está en validación exploratoria antes de integrarse al core regional principal."
        )

'''

insert_marker = '''# ============================================================
# TAB 6 — DATA STATUS
# ============================================================
'''

if "TAB 6 — REINSURANCE VIEW" not in app_text:
    app_text = app_text.replace(insert_marker, reinsurance_section + "\n" + insert_marker)
    print("Sección Reinsurance View insertada.")
else:
    print("Sección Reinsurance View ya existía. No se duplicó.")

# Renombrar comentario de Data Status si ahora quedó como TAB 6
app_text = app_text.replace(
    "# TAB 6 — DATA STATUS",
    "# TAB 7 — DATA STATUS"
)

app_text = app_text.replace(
    "# TAB 7 — REPORTS / EXPORT",
    "# TAB 8 — REPORTS / EXPORT"
)

app_text = app_text.replace(
    "# TAB 8 — DATA TABLE",
    "# TAB 9 — DATA TABLE"
)

APP_FILE.write_text(app_text, encoding="utf-8")

print("streamlit_app.py actualizado correctamente con Reinsurance View.")