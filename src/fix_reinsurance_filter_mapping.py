from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_fix_reinsurance_filter.py")

text = APP_FILE.read_text(encoding="utf-8")
BACKUP_FILE.write_text(text, encoding="utf-8")

print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Asegurar función de mapping
# ============================================================

mapping_function = r'''

def normalize_lob_text(value):
    if value is None:
        return ""
    return str(value).strip().upper()


def map_lob_to_indicadores_gestion(selected_line):
    """
    Traduce nombres de ramos desde Ciudades y Ramos hacia Indicadores de Gestión.
    Fasecolda usa nombres distintos entre fuentes.
    """

    if selected_line == "TODOS":
        return None

    mapping = {
        "AUTOMOVILES": "Autos",
        "AUTOS": "Autos",
        "INCENDIO Y LUCRO CESANTE": "Incendio y Lucro",
        "INCENDIO Y LUCRO": "Incendio y Lucro",
        "CUMPLIMIENTO": "Cumplimiento",
        "TRANSPORTE": "Transporte",
        "RESPONSABILIDAD CIVIL": "Responsabilidad Civil",
        "TERREMOTO": "Terremoto",
        "VIDA GRUPO": "Vida grupo",
        "VIDA INDIVIDUAL": "Vida individual",
        "SALUD": "Salud",
        "RIESGOS LABORALES": "Riesgos Laborales",
        "SOAT": "Soat",
        "HOGAR": "Hogar",
        "AVIACION": "Aviación",
        "AVIACIÓN": "Aviación",
        "AGROPECUARIO": "Agropecuario",
        "SUSTRACCION": "Sustracción",
        "SUSTRACCIÓN": "Sustracción",
        "DESEMPLEO": "Desempleo",
        "EXEQUIAS": "Exequias",
        "MANEJO": "Manejo",
        "CORRIENTE DEBIL": "Corriente Débil",
        "CORRIENTE DÉBIL": "Corriente Débil",
        "SEGUROS DE CREDITO": "Seguros de Credito",
        "SEGUROS DE CRÉDITO": "Seguros de Credito",
        "MINAS Y PETROLEOS": "Minas y Petróleos",
        "MINAS Y PETRÓLEOS": "Minas y Petróleos",
        "MONTAJE Y ROTURA": "Montaje y Rotura",
        "INGENIERIA": "Ingenieria",
        "INGENIERÍA": "Ingenieria",
        "TODO RIESGO CONTRATISTA": "Todo Riesgo Cont.",
        "NAVEGACION Y CASCO": "Nav.yCasco",
        "NAVEGACIÓN Y CASCO": "Nav.yCasco",
        "VIDRIOS": "Vidrios",
        "DECENAL": "Decenal",
        "BEPS": "BEPS",
        "ACCIDENTES PERSONALES": "Accidentes P",
        "ACCIDENTES P": "Accidentes P",
        "OTROS DAÑOS": "Otros Daños",
        "OTROS PERSONAS": "Otros Personas",
    }

    normalized = normalize_lob_text(selected_line)
    return mapping.get(normalized)
'''

if "def map_lob_to_indicadores_gestion" not in text:
    insert_after = '''def fix_year_axis(fig, years):
    years = sorted(pd.Series(years).dropna().astype(int).unique())
    fig.update_xaxes(
        tickmode="array",
        tickvals=years,
        tickformat="d"
    )
    return fig
'''
    text = text.replace(insert_after, insert_after + mapping_function)
    print("Función de mapping agregada.")
else:
    print("La función de mapping ya existía.")

# ============================================================
# 2. Reemplazar bloque completo de filtros dentro de Reinsurance View
# ============================================================

start_marker = '''        re_df = indicadores_df[indicadores_df["country"] == selected_country].copy()

        # Filtros alineados con la barra lateral
'''

end_marker = '''        # Indicadores de Gestión no trae ciudad; por eso no aplicamos filtro de ciudad
'''

new_filter_block = '''        re_df = indicadores_df[indicadores_df["country"] == selected_country].copy()

        # Normalizar textos para comparar mejor entre fuentes
        re_df["company_standard_norm"] = re_df["company_standard"].astype(str).str.strip().str.upper()
        re_df["line_of_business_standard_norm"] = re_df["line_of_business_standard"].astype(str).str.strip().str.upper()

        # Filtros alineados con la barra lateral
        if selected_company != "TODAS":
            selected_company_norm = str(selected_company).strip().upper()
            re_df = re_df[re_df["company_standard_norm"] == selected_company_norm]

        if selected_line != "TODOS":
            mapped_line = map_lob_to_indicadores_gestion(selected_line)

            if mapped_line is None:
                st.warning(
                    f"El ramo seleccionado '{selected_line}' no tiene mapeo disponible "
                    "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                    "hasta que agreguemos esta equivalencia al diccionario de ramos."
                )
                re_df = re_df.iloc[0:0]
            else:
                mapped_line_norm = str(mapped_line).strip().upper()
                re_df = re_df[re_df["line_of_business_standard_norm"] == mapped_line_norm]

                if re_df.empty:
                    st.warning(
                        f"El ramo seleccionado '{selected_line}' fue mapeado como '{mapped_line}', "
                        "pero no se encontraron registros en Indicadores de Gestión 2025."
                    )
                else:
                    st.info(
                        f"Ramo mapeado para Indicadores de Gestión: '{selected_line}' → '{mapped_line}'."
                    )

'''

if start_marker not in text or end_marker not in text:
    raise ValueError(
        "No pude encontrar los marcadores exactos dentro de Reinsurance View. "
        "No se modificó el archivo."
    )

start = text.index(start_marker)
end = text.index(end_marker)

text = text[:start] + new_filter_block + text[end:]

APP_FILE.write_text(text, encoding="utf-8")

print("Filtro de Reinsurance View corregido correctamente.")
print("Ahora vuelve a correr: streamlit run app\\streamlit_app.py")