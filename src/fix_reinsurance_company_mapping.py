from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_fix_company_mapping.py")

text = APP_FILE.read_text(encoding="utf-8")
BACKUP_FILE.write_text(text, encoding="utf-8")

print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Asegurar función de carga de mapping de compañías
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

if "def load_company_mapping" not in text:
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
    text = text.replace(marker, marker + load_company_mapping_function)
    print("Función load_company_mapping agregada.")
else:
    print("Función load_company_mapping ya existía.")

# ============================================================
# 2. Asegurar carga de company_mapping_df
# ============================================================

if "company_mapping_df = load_company_mapping()" not in text:
    text = text.replace(
        "lob_mapping_df = load_lob_mapping()",
        "lob_mapping_df = load_lob_mapping()\ncompany_mapping_df = load_company_mapping()"
    )
    print("Carga de company_mapping_df agregada.")
else:
    print("company_mapping_df ya se estaba cargando.")

# ============================================================
# 3. Asegurar función de lookup de compañías
# ============================================================

lookup_function = r'''

def map_company_using_mapping_table(selected_company, target_source, country="COLOMBIA"):
    """
    Busca la compañía seleccionada en dim_company_mapping y devuelve
    el nombre equivalente para la fuente objetivo.
    """

    if selected_company == "TODAS":
        return None

    if "company_mapping_df" not in globals() or company_mapping_df.empty:
        return None

    mapping = company_mapping_df.copy()

    mapping["country_norm"] = mapping["country"].astype(str).str.strip().str.upper()
    mapping["source_norm"] = mapping["source"].astype(str).str.strip().str.upper()
    mapping["source_company_norm"] = mapping["source_company"].astype(str).str.strip().str.upper()
    mapping["standard_company_norm"] = mapping["standard_company"].astype(str).str.strip().str.upper()
    mapping["group_name_norm"] = mapping["group_name"].astype(str).str.strip().str.upper()

    selected_norm = str(selected_company).strip().upper()
    target_source_norm = str(target_source).strip().upper()
    country_norm = str(country).strip().upper()

    matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (
            (mapping["source_company_norm"] == selected_norm) |
            (mapping["standard_company_norm"] == selected_norm) |
            (mapping["group_name_norm"] == selected_norm)
        )
    ]

    if matches.empty:
        return None

    standard_company = matches.iloc[0]["standard_company_norm"]
    group_name = matches.iloc[0]["group_name_norm"]

    target_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["standard_company_norm"] == standard_company)
    ]

    if not target_matches.empty:
        return target_matches.iloc[0]["source_company"]

    target_group_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["group_name_norm"] == group_name)
    ]

    if not target_group_matches.empty:
        return target_group_matches.iloc[0]["source_company"]

    return None
'''

if "def map_company_using_mapping_table" not in text:
    marker = '''# ============================================================
# CARGA Y NORMALIZACIÓN DE DATOS
# ============================================================
'''
    text = text.replace(marker, lookup_function + "\n" + marker)
    print("Función map_company_using_mapping_table agregada.")
else:
    print("Función map_company_using_mapping_table ya existía.")

# ============================================================
# 4. Reemplazar el bloque de filtro de compañía dentro de Reinsurance View
# ============================================================

old_block_1 = '''        if selected_company != "TODAS":
            selected_company_norm = str(selected_company).strip().upper()
            re_df = re_df[re_df["company_standard_norm"] == selected_company_norm]
'''

new_block = '''        if selected_company != "TODAS":
            mapped_company = map_company_using_mapping_table(
                selected_company,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country
            )

            if mapped_company is None:
                st.warning(
                    f"La compañía seleccionada '{selected_company}' no tiene mapeo disponible "
                    "en Indicadores de Gestión 2025. La vista de reaseguro se mostrará vacía "
                    "hasta que agreguemos esta equivalencia al mapping de compañías."
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

if old_block_1 in text:
    text = text.replace(old_block_1, new_block)
    print("Bloque de filtro de compañía reemplazado.")
else:
    print("No se encontró el bloque simple de compañía. Intentando reemplazo por marcadores...")

    start_marker = '''        if selected_company != "TODAS":'''
    end_marker = '''        if selected_line != "TODOS":'''

    start = text.find(start_marker)
    end = text.find(end_marker, start)

    if start == -1 or end == -1:
        raise ValueError("No pude encontrar el bloque de compañía dentro de Reinsurance View.")

    text = text[:start] + new_block + "\n" + text[end:]
    print("Bloque de compañía reemplazado usando marcadores.")

APP_FILE.write_text(text, encoding="utf-8")

print("Corrección terminada.")
print("Ahora ejecuta: streamlit run app\\streamlit_app.py")