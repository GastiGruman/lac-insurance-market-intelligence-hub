from pathlib import Path
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path("data/processed/ciudades_ramos_2015_2025_clean.csv")
DB_FILE = Path("data/database/insurance_market.duckdb")

TABLE_NAME = "fact_fasecolda_market"

# ============================================================
# CARGA DEL ARCHIVO LIMPIO
# ============================================================

print("Leyendo archivo limpio 2015-2025...")
df = pd.read_csv(INPUT_FILE)

print("Tamaño del dataset:")
print(df.shape)

print("\nRango de fechas:")
df["date"] = pd.to_datetime(df["date"], errors="coerce")
print(df["date"].min(), "->", df["date"].max())

print("\nAños disponibles:")
print(sorted(df["year"].dropna().unique()))

print("\nTipos de valor:")
print(df["value_type"].value_counts())

# ============================================================
# CARGA A DUCKDB
# ============================================================

print("\nConectando a DuckDB...")

conn = duckdb.connect(str(DB_FILE))

conn.execute(f"""
    CREATE OR REPLACE TABLE {TABLE_NAME} AS
    SELECT *
    FROM df
""")

summary = conn.execute(f"""
    SELECT
        country,
        year,
        value_type,
        COUNT(*) AS records,
        SUM(value) AS total_value
    FROM {TABLE_NAME}
    GROUP BY country, year, value_type
    ORDER BY country, year, value_type
""").fetchdf()

print("\nResumen cargado en DuckDB:")
print(summary)

total_rows = conn.execute(f"""
    SELECT COUNT(*) AS total_rows
    FROM {TABLE_NAME}
""").fetchdf()

print("\nTotal de registros cargados:")
print(total_rows)

conn.close()

print("\nBase actualizada correctamente.")
print(f"Tabla actualizada: {TABLE_NAME}")
print(f"Base de datos: {DB_FILE}")