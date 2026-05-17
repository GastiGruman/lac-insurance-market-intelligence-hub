from pathlib import Path
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_FILE = Path("data/database/insurance_market.duckdb")

LOB_MAPPING_FILE = Path("data/mappings/line_of_business_mapping.csv")
COMPANY_MAPPING_FILE = Path("data/mappings/company_mapping.csv")

LOB_TABLE_NAME = "dim_line_of_business_mapping"
COMPANY_TABLE_NAME = "dim_company_mapping"


# ============================================================
# FUNCIONES
# ============================================================

def read_csv_flexible(path):
    """
    Lee CSVs creados en Windows/Bloc de notas.
    Primero intenta UTF-8 y si falla usa latin1.
    """
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def normalize_text_series(series, upper=True):
    result = series.fillna("").astype(str).str.strip()
    if upper:
        result = result.str.upper()
    return result


# ============================================================
# CARGAR MAPPING DE RAMOS
# ============================================================

print("Leyendo mapping de ramos...")

lob_mapping = read_csv_flexible(LOB_MAPPING_FILE)

print("Tamaño del mapping de ramos:")
print(lob_mapping.shape)

required_lob_columns = [
    "country",
    "source",
    "source_line_of_business",
    "standard_line_of_business",
    "lob_group",
    "notes"
]

missing_lob_columns = [col for col in required_lob_columns if col not in lob_mapping.columns]

if missing_lob_columns:
    raise ValueError(f"Faltan columnas requeridas en el mapping de ramos: {missing_lob_columns}")

lob_mapping["country"] = normalize_text_series(lob_mapping["country"])
lob_mapping["source"] = normalize_text_series(lob_mapping["source"], upper=False)
lob_mapping["source_line_of_business"] = normalize_text_series(lob_mapping["source_line_of_business"], upper=False)
lob_mapping["standard_line_of_business"] = normalize_text_series(lob_mapping["standard_line_of_business"])
lob_mapping["lob_group"] = normalize_text_series(lob_mapping["lob_group"])
lob_mapping["notes"] = normalize_text_series(lob_mapping["notes"], upper=False)

lob_mapping["source_norm"] = normalize_text_series(lob_mapping["source"])
lob_mapping["source_line_of_business_norm"] = normalize_text_series(lob_mapping["source_line_of_business"])
lob_mapping["standard_line_of_business_norm"] = normalize_text_series(lob_mapping["standard_line_of_business"])

duplicate_lob_keys = lob_mapping.duplicated(
    subset=["country", "source_norm", "source_line_of_business_norm"],
    keep=False
)

if duplicate_lob_keys.any():
    print("\nWARNING: Hay claves duplicadas en el mapping de ramos:")
    print(
        lob_mapping.loc[
            duplicate_lob_keys,
            [
                "country",
                "source",
                "source_line_of_business",
                "standard_line_of_business",
                "lob_group"
            ]
        ]
    )
else:
    print("\nNo se encontraron claves duplicadas en el mapping de ramos.")

print("\nResumen mapping de ramos por fuente:")
print(
    lob_mapping
    .groupby(["country", "source"], as_index=False)
    .agg(
        mappings=("source_line_of_business", "count"),
        standard_lines=("standard_line_of_business", "nunique"),
        groups=("lob_group", "nunique")
    )
)

lob_normalized_file = Path("data/mappings/line_of_business_mapping_normalized.csv")
lob_mapping.to_csv(lob_normalized_file, index=False, encoding="utf-8-sig")

print("\nCopia normalizada de ramos guardada en:")
print(lob_normalized_file)


# ============================================================
# CARGAR MAPPING DE COMPAÑÍAS
# ============================================================

print("\nLeyendo mapping de compañías...")

company_mapping = read_csv_flexible(COMPANY_MAPPING_FILE)

print("Tamaño del mapping de compañías:")
print(company_mapping.shape)

required_company_columns = [
    "country",
    "source",
    "source_company",
    "standard_company",
    "group_name",
    "company_type",
    "notes"
]

missing_company_columns = [col for col in required_company_columns if col not in company_mapping.columns]

if missing_company_columns:
    raise ValueError(f"Faltan columnas requeridas en el mapping de compañías: {missing_company_columns}")

company_mapping["country"] = normalize_text_series(company_mapping["country"])
company_mapping["source"] = normalize_text_series(company_mapping["source"], upper=False)
company_mapping["source_company"] = normalize_text_series(company_mapping["source_company"], upper=False)
company_mapping["standard_company"] = normalize_text_series(company_mapping["standard_company"])
company_mapping["group_name"] = normalize_text_series(company_mapping["group_name"])
company_mapping["company_type"] = normalize_text_series(company_mapping["company_type"])
company_mapping["notes"] = normalize_text_series(company_mapping["notes"], upper=False)

company_mapping["source_norm"] = normalize_text_series(company_mapping["source"])
company_mapping["source_company_norm"] = normalize_text_series(company_mapping["source_company"])
company_mapping["standard_company_norm"] = normalize_text_series(company_mapping["standard_company"])
company_mapping["group_name_norm"] = normalize_text_series(company_mapping["group_name"])

duplicate_company_keys = company_mapping.duplicated(
    subset=["country", "source_norm", "source_company_norm"],
    keep=False
)

if duplicate_company_keys.any():
    print("\nWARNING: Hay claves duplicadas en el mapping de compañías:")
    print(
        company_mapping.loc[
            duplicate_company_keys,
            [
                "country",
                "source",
                "source_company",
                "standard_company",
                "group_name",
                "company_type"
            ]
        ]
    )
else:
    print("\nNo se encontraron claves duplicadas en el mapping de compañías.")

print("\nResumen mapping de compañías por fuente:")
print(
    company_mapping
    .groupby(["country", "source"], as_index=False)
    .agg(
        mappings=("source_company", "count"),
        standard_companies=("standard_company", "nunique"),
        groups=("group_name", "nunique"),
        company_types=("company_type", "nunique")
    )
)

company_normalized_file = Path("data/mappings/company_mapping_normalized.csv")
company_mapping.to_csv(company_normalized_file, index=False, encoding="utf-8-sig")

print("\nCopia normalizada de compañías guardada en:")
print(company_normalized_file)


# ============================================================
# CARGAR A DUCKDB
# ============================================================

print("\nConectando a DuckDB...")

conn = duckdb.connect(str(DB_FILE))

conn.execute(f"""
    CREATE OR REPLACE TABLE {LOB_TABLE_NAME} AS
    SELECT *
    FROM lob_mapping
""")

conn.execute(f"""
    CREATE OR REPLACE TABLE {COMPANY_TABLE_NAME} AS
    SELECT *
    FROM company_mapping
""")

lob_summary = conn.execute(f"""
    SELECT
        country,
        source,
        COUNT(*) AS mappings,
        COUNT(DISTINCT standard_line_of_business) AS standard_lines,
        COUNT(DISTINCT lob_group) AS lob_groups
    FROM {LOB_TABLE_NAME}
    GROUP BY country, source
    ORDER BY country, source
""").fetchdf()

company_summary = conn.execute(f"""
    SELECT
        country,
        source,
        COUNT(*) AS mappings,
        COUNT(DISTINCT standard_company) AS standard_companies,
        COUNT(DISTINCT group_name) AS groups,
        COUNT(DISTINCT company_type) AS company_types
    FROM {COMPANY_TABLE_NAME}
    GROUP BY country, source
    ORDER BY country, source
""").fetchdf()

print("\nTabla de mapping de ramos cargada en DuckDB:")
print(lob_summary)

print("\nTabla de mapping de compañías cargada en DuckDB:")
print(company_summary)

lob_rows = conn.execute(f"""
    SELECT COUNT(*) AS total_rows
    FROM {LOB_TABLE_NAME}
""").fetchdf()

company_rows = conn.execute(f"""
    SELECT COUNT(*) AS total_rows
    FROM {COMPANY_TABLE_NAME}
""").fetchdf()

print("\nTotal registros dim_line_of_business_mapping:")
print(lob_rows)

print("\nTotal registros dim_company_mapping:")
print(company_rows)

conn.close()

print("\nCarga de mappings completada correctamente.")
print(f"Tabla creada/actualizada: {LOB_TABLE_NAME}")
print(f"Tabla creada/actualizada: {COMPANY_TABLE_NAME}")
print(f"Base de datos: {DB_FILE}")