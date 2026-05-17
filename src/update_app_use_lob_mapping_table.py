from pathlib import Path

APP_FILE = Path("app/streamlit_app.py")
BACKUP_FILE = Path("app/streamlit_app_backup_before_lob_mapping_table.py")

text = APP_FILE.read_text(encoding="utf-8")
BACKUP_FILE.write_text(text, encoding="utf-8")

print(f"Backup creado en: {BACKUP_FILE}")

# ============================================================
# 1. Agregar función para cargar mapping de ramos desde DuckDB
# ============================================================

load_mapping_function = '''

@st.cache_data
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

marker = '''@st.cache_data
def load_indicadores_gestion_validation():
    validation_path = Path("outputs/indicadores_gestion_2025_validation_report.csv")
    if validation_path.exists():
        return pd.read_csv(validation_path)
    return pd.DataFrame(columns=["test_name", "result", "detail"])
'''

if "def load_lob_mapping" not in text:
    text = text.replace(marker, marker + load_mapping_function)
    print("Función load_lob_mapping agregada.")
else:
    print("La función load_lob_mapping ya existía.")

# ============================================================
# 2. Cargar lob_mapping_df junto con los otros dataframes
# ============================================================

old_load_block = '''df = load_market_core()
validation_df = load_validation_report()
indicadores_df = load_indicadores_gestion_2025()
indicadores_validation_df = load_indicadores_gestion_validation()
'''

new_load_block = '''df = load_market_core()
validation_df = load_validation_report()
indicadores_df = load_indicadores_gestion_2025()
indicadores_validation_df = load_indicadores_gestion_validation()
lob_mapping_df = load_lob_mapping()
'''

if "lob_mapping_df = load_lob_mapping()" not in text:
    text = text.replace(old_load_block, new_load_block)
    print("Carga de lob_mapping_df agregada.")
else:
    print("lob_mapping_df ya se estaba cargando.")

# ============================================================
# 3. Agregar función de lookup desde tabla formal
# ============================================================

lookup_function = r'''

def map_lob_using_mapping_table(selected_line, target_source, country="COLOMBIA"):
    """
    Busca el ramo seleccionado en dim_line_of_business_mapping y devuelve
    el nombre equivalente para la fuente objetivo.

    Ejemplo:
    selected_line = "INCENDIO Y LUCRO CESANTE"
    target_source = "FASECOLDA - INDICADORES DE GESTION"
    devuelve "Incendio y Lucro"
    """

    if selected_line == "TODOS":
        return None

    if "lob_mapping_df" not in globals() or lob_mapping_df.empty:
        return None

    mapping = lob_mapping_df.copy()

    mapping["country_norm"] = mapping["country"].astype(str).str.strip().str.upper()
    mapping["source_norm"] = mapping["source"].astype(str).str.strip().str.upper()
    mapping["source_line_of_business_norm"] = (
        mapping["source_line_of_business"].astype(str).str.strip().str.upper()
    )
    mapping["standard_line_of_business_norm"] = (
        mapping["standard_line_of_business"].astype(str).str.strip().str.upper()
    )

    selected_norm = str(selected_line).strip().upper()
    target_source_norm = str(target_source).strip().upper()
    country_norm = str(country).strip().upper()

    # Primero buscamos cuál es el estándar del ramo seleccionado,
    # sin importar desde qué fuente vino.
    standard_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (
            (mapping["source_line_of_business_norm"] == selected_norm) |
            (mapping["standard_line_of_business_norm"] == selected_norm)
        )
    ]

    if standard_matches.empty:
        return None

    standard_lob = standard_matches.iloc[0]["standard_line_of_business_norm"]

    # Luego buscamos cómo se llama ese estándar en la fuente objetivo.
    target_matches = mapping[
        (mapping["country_norm"] == country_norm) &
        (mapping["source_norm"] == target_source_norm) &
        (mapping["standard_line_of_business_norm"] == standard_lob)
    ]

    if target_matches.empty:
        return None

    return target_matches.iloc[0]["source_line_of_business"]
'''

insert_after = '''def map_lob_to_indicadores_gestion(selected_line):
    """
    Traduce nombres de ramos desde Ciudades y Ramos hacia Indicadores de Gestión.
    Fasecolda usa nombres distintos entre fuentes.
    """
'''

# Si existe el diccionario manual, no lo borramos todavía. Solo agregamos función nueva antes de la sección de carga.
safe_insert_marker = '''# ============================================================
# CARGA Y NORMALIZACIÓN DE DATOS
# ============================================================
'''

if "def map_lob_using_mapping_table" not in text:
    text = text.replace(safe_insert_marker, lookup_function + "\n" + safe_insert_marker)
    print("Función map_lob_using_mapping_table agregada.")
else:
    print("La función map_lob_using_mapping_table ya existía.")

# ============================================================
# 4. Reemplazar uso de map_lob_to_indicadores_gestion en Reinsurance View
# ============================================================

old_line = '''            mapped_line = map_lob_to_indicadores_gestion(selected_line)
'''

new_line = '''            mapped_line = map_lob_using_mapping_table(
                selected_line,
                target_source="FASECOLDA - INDICADORES DE GESTION",
                country=selected_country
            )
'''

if old_line in text:
    text = text.replace(old_line, new_line)
    print("Reinsurance View actualizada para usar dim_line_of_business_mapping.")
else:
    print("No se encontró la línea exacta de mapping manual. Puede que ya esté actualizada.")

APP_FILE.write_text(text, encoding="utf-8")

print("streamlit_app.py actualizado correctamente.")
print("Ahora ejecuta: streamlit run app\\streamlit_app.py")