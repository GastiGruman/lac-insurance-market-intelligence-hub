from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_before_company_mapping_table.py")

text = APP_FILE.read_text(encoding="utf-8")
BACKUP_FILE.write_text(text, encoding="utf-8")

print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Agregar función para cargar mapping de compañías desde DuckDB
# ============================================================

load_company_mapping_function = '''

@st.cache_data
def load_company_mapping():
    try:
        conn = duckdb.connect(str(DB_PATH))
        df = conn.execute("""
            SELECT *
            FROM dim_company_mapping
        """).fetchdf()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()
'''

marker = '''@st.cache_data
def load_lob_mapping():
    try:
        conn = duckdb.connect(str(DB_PATH))
        df = conn.execute("""
            SELECT *
            FROM dim_line_of_business_mapping
        """).fetchdf()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()
'''

if "def load_company_mapping" not in text:
    text = text.replace(marker, marker + load_company_mapping_function)
    print("Función load_company_mapping agregada.")
else:
    print("La función load_company_mapping ya existía.")

# ============================================================
# 2. Cargar company_mapping_df junto con los otros dataframes
# ============================================================

old_load_block = '''df = load_market_core()
validation_df = load_validation_report()
indicadores_df = load_indicadores_gestion_2025()
indicadores_validation_df = load_indicadores_gestion_validation()
lob_mapping_df = load_lob_mapping()
'''

new_load_block = '''df = load_market_core()
validation_df = load_validation_report()
indicadores_df = load_indicadores_gestion_2025()
indicadores_validation_df = load_indicadores_gestion_validation()
lob_mapping_df = load_lob_mapping()
company_mapping_df = load_company_mapping()
'''

if "company_mapping_df = load_company_mapping()" not in text:
    text = text.replace(old_load_block, new_load_block)
    print("Carga de company_mapping_df agregada.")
else:
    print("company_mapping_df ya se estaba cargando.")

# ============================================================
# 3. Agregar función de lookup de compañía desde tabla formal
# ============================================================

lookup_function = r'''

def map_company_using_mapping_table(selected_company, target_source, country="COLOMBIA"):
    """
    Busca la compañía seleccionada en dim_company_mapping y devuelve
    el nombre equivalente para la fuente objetivo.

    Ejemplo:
    selected_company = "MAPFRE"
    target_source = "FASECOLDA - INDICADORES DE GESTION"
    devuelve "MAPFRE" o el nombre correspondiente en esa fuente.
    """

    if selected_company == "TODAS":
        return None

    if "company_mapping_df" not in globals() or company_mapping_df.empty:
        return None

    mapping = company_mapping_df.copy()

    mapping["country_norm"] = mapping["country"].astype(str).str.strip().str.upper()
    mapping["source_norm"] = mapping["source"].astype(str).str.strip().str.upper()
    mapping["source_company_norm"] = (
        mapping["source_company"].astype(str).str.strip().str.upper()
    )
    mapping["standard_company_norm"] = (
        mapping["standard_company"].astype(str).str.strip().str.upper()
    )
    mapping["group_name_norm"] = (
        mapping["group_name"].astype(str).str.strip().str.upper()
    )

    selected_norm = str(selected_company).strip().upper()
    target_source_norm = str(target_source).strip().upper()
    country_norm = str(country).strip().upper()

    # Primero buscamos la compañía seleccionada en cualquier forma conocida.
    standard_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (
            (mapping["source_company_norm"] == selected_norm) |
            (mapping["standard_company_norm"] == selected_norm) |
            (mapping["group_name_norm"] == selected_norm)
        )
    ]

    if standard_matches.empty:
        return None

    standard_company = standard_matches.iloc[0]["standard_company_norm"]
    group_name = standard_matches.iloc[0]["group_name_norm"]

    # Luego buscamos cómo aparece esa compañía en la fuente objetivo.
    # Primero intentamos por standard_company.
    target_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["standard_company_norm"] == standard_company)
    ]

    if not target_matches.empty:
        return target_matches.iloc[0]["source_company"]

    # Si no hay match exacto por entidad, intentamos por grupo.
    target_group_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["group_name_norm"] == group_name)
    ]

    if not target_group_matches.empty:
        return target_group_matches.iloc[0]["source_company"]

    return None
'''

safe_insert_marker = '''# ============================================================
# CARGA Y NORMALIZACIÓN DE DATOS
# ============================================================
'''

if "def map_company_using_mapping_table" not in text:
    text = text.replace(safe_insert_marker, lookup_function + "\n" + safe_insert_marker)
    print("Función map_company_using_mapping_table agregada.")
else:
    print("La función map_company_using_mapping_table ya existía.")

# ============================================================
# 4. Reemplazar filtro de compañía dentro de Reinsurance View
# ============================================================

old_company_block = '''        if selected_company != "TODAS":
            selected_company_norm = str(selected_company).strip().upper()
            re_df = re_df[re_df["company_standard_norm"] == selected_company_norm]
'''

new_company_block = '''        if selected_company != "TODAS":
            mapped_company = map_company_using_mapping_table(
                selected_company,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country
            )

            if mapped_company is None:
                st.warning(
                    f"La compañía seleccionada '{selected_company}' no tiene mapeo disponible "
                    "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                    "hasta que agreguemos esta equivalencia al diccionario de compañías."
                )
                re_df = re_df.iloc[0:0]
            else:
                mapped_company_norm = str(mapped_company).strip().upper()
                re_df = re_df[re_df["company_standard_norm"] == mapped_company_norm]

                if re_df.empty:
                    st.warning(
                        f"La compañía seleccionada '{selected_company}' fue mapeada como "
                        f"'{mapped_company}', pero no se encontraron registros en Indicadores de Gestión 2025."
                    )
                else:
                    st.info(
                        f"Compañía mapeada para Indicadores de Gestión: "
                        f"'{selected_company}' → '{mapped_company}'."
                    )
'''

if old_company_block in text:
    text = text.replace(old_company_block, new_company_block)
    print("Filtro de compañía en Reinsurance View actualizado con dim_company_mapping.")
else:
    print("No se encontró el bloque exacto de filtro de compañía. Puede que ya haya sido modificado.")

APP_FILE.write_text(text, encoding="utf-8")

print("streamlit_app.py actualizado correctamente con company mapping.")
print("Ahora ejecuta: streamlit run app\\streamlit_app.py")