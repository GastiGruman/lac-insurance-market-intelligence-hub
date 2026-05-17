from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_before_lob_mapping.py")

text = APP_FILE.read_text(encoding="utf-8")

BACKUP_FILE.write_text(text, encoding="utf-8")
print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Agregar función de mapeo de ramos
# ============================================================

mapping_function = r'''

def map_lob_to_indicadores_gestion(selected_line):
    """
    Traduce nombres de ramos desde Ciudades y Ramos hacia Indicadores de Gestión.
    Esto es necesario porque Fasecolda usa nombres distintos entre fuentes.
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
        "AGROPECUARIO": "Agropecuario",
        "SUSTRACCION": "Sustracción",
        "DESEMPLEO": "Desempleo",
        "EXEQUIAS": "Exequias",
        "MANEJO": "Manejo",
        "CORRIENTE DEBIL": "Corriente Débil",
        "SEGUROS DE CREDITO": "Seguros de Credito",
        "MINAS Y PETROLEOS": "Minas y Petróleos",
        "MONTAJE Y ROTURA": "Montaje y Rotura",
        "INGENIERIA": "Ingenieria",
        "TODO RIESGO CONTRATISTA": "Todo Riesgo Cont.",
        "NAVEGACION Y CASCO": "Nav.yCasco",
        "VIDRIOS": "Vidrios",
        "DECENAL": "Decenal",
        "BEPS": "BEPS",
    }

    normalized = str(selected_line).strip().upper()

    return mapping.get(normalized)
'''

insert_after = '''def fix_year_axis(fig, years):
    years = sorted(pd.Series(years).dropna().astype(int).unique())
    fig.update_xaxes(
        tickmode="array",
        tickvals=years,
        tickformat="d"
    )
    return fig
'''

if "def map_lob_to_indicadores_gestion" not in text:
    text = text.replace(insert_after, insert_after + mapping_function)
    print("Función de mapeo de ramos agregada.")
else:
    print("La función de mapeo ya existía. No se duplicó.")

# ============================================================
# 2. Reemplazar filtro de ramo dentro de Reinsurance View
# ============================================================

old_block = '''        if selected_line != "TODOS":
            re_df = re_df[re_df["line_of_business_standard"] == selected_line]
'''

new_block = '''        if selected_line != "TODOS":
            mapped_line = map_lob_to_indicadores_gestion(selected_line)

            if mapped_line is None:
                st.warning(
                    f"El ramo seleccionado '{selected_line}' no tiene mapeo disponible "
                    "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                    "hasta que agreguemos esta equivalencia al diccionario de ramos."
                )
                re_df = re_df.iloc[0:0]
            else:
                re_df = re_df[re_df["line_of_business_standard"] == mapped_line]

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

if old_block in text:
    text = text.replace(old_block, new_block)
    print("Filtro de ramo en Reinsurance View actualizado con mapping.")
else:
    print("No se encontró el bloque exacto del filtro de ramo. Puede que ya haya sido modificado.")

APP_FILE.write_text(text, encoding="utf-8")

print("streamlit_app.py actualizado correctamente con mapping de ramos.")