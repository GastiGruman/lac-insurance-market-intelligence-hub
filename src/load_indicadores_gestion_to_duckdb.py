from pathlib import Path
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path("data/processed/indicadores_gestion_2025_core.csv")
DB_FILE = Path("data/database/insurance_market.duckdb")

TABLE_NAME = "fact_indicadores_gestion_2025"

# ============================================================
# CARGA DEL ARCHIVO
# ============================================================

print("Leyendo Indicadores de Gestión 2025...")
df = pd.read_csv(INPUT_FILE)

print("Tamaño del dataset:")
print(df.shape)

print("\nColumnas:")
print(df.columns.tolist())

# Normalización básica
df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")

# ============================================================
# CONTROLES PREVIOS
# ============================================================

print("\nRango de fechas:")
print(df["period_date"].min(), "->", df["period_date"].max())

print("\nMétricas encontradas:")
print(df["metric_name"].value_counts())

print("\nRamos encontrados:")
print(sorted(df["line_of_business_standard"].dropna().unique()))

print("\nPrimeras filas:")
print(df.head(20))

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
        line_of_business_standard,
        metric_name,
        COUNT(*) AS records,
        SUM(metric_value) AS total_value
    FROM {TABLE_NAME}
    GROUP BY country, year, line_of_business_standard, metric_name
    ORDER BY country, year, line_of_business_standard, metric_name
""").fetchdf()

print("\nResumen cargado en DuckDB:")
print(summary.head(100))

total_rows = conn.execute(f"""
    SELECT COUNT(*) AS total_rows
    FROM {TABLE_NAME}
""").fetchdf()

print("\nTotal de registros cargados:")
print(total_rows)

metric_summary = conn.execute(f"""
    SELECT
        metric_name,
        COUNT(*) AS records,
        SUM(metric_value) AS total_value
    FROM {TABLE_NAME}
    GROUP BY metric_name
    ORDER BY metric_name
""").fetchdf()

print("\nResumen por métrica:")
print(metric_summary)

conn.close()

print("\nCarga completada correctamente.")
print(f"Tabla creada/actualizada: {TABLE_NAME}")
print(f"Base de datos: {DB_FILE}")