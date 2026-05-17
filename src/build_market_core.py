from pathlib import Path
from datetime import datetime
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path("data/processed/ciudades_ramos_2015_2025_clean.csv")
DB_FILE = Path("data/database/insurance_market.duckdb")

OUTPUT_FILE = Path("data/processed/market_core_colombia.csv")

COUNTRY = "COLOMBIA"
REGION = "LATIN AMERICA AND CARIBBEAN"
REGULATOR = "FASECOLDA"
SOURCE = "FASECOLDA - CIUDADES Y RAMOS"
CURRENCY = "COP"

# ============================================================
# CARGA DE DATOS
# ============================================================

print("Leyendo archivo limpio de Ciudades y Ramos 2015-2025...")
df = pd.read_csv(INPUT_FILE)

print("Tamaño inicial:")
print(df.shape)

print("\nColumnas disponibles:")
print(df.columns.tolist())

# ============================================================
# VALIDACIÓN DE COLUMNAS NECESARIAS
# ============================================================

required_columns = [
    "company",
    "value_type",
    "line_of_business",
    "city",
    "value",
    "date",
    "source_file",
    "year",
    "month",
    "country",
    "source"
]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(f"Faltan columnas requeridas en el archivo limpio: {missing_columns}")

# ============================================================
# NORMALIZACIÓN DE TIPOS
# ============================================================

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["month"] = pd.to_numeric(df["month"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

# Eliminar registros sin datos básicos
df = df.dropna(subset=["date", "year", "month", "value"])

df["year"] = df["year"].astype(int)
df["month"] = df["month"].astype(int)

# Normalizar textos
df["company"] = df["company"].astype(str).str.strip().str.upper()
df["value_type"] = df["value_type"].astype(str).str.strip().str.upper()
df["line_of_business"] = df["line_of_business"].astype(str).str.strip().str.upper()
df["city"] = df["city"].astype(str).str.strip().str.upper()
df["country"] = df["country"].astype(str).str.strip().str.upper()
df["source"] = df["source"].astype(str).str.strip().str.upper()
df["source_file"] = df["source_file"].astype(str).str.strip()

# ============================================================
# CREAR MARKET CORE EN FORMATO ESTÁNDAR REGIONAL
# ============================================================

print("\nConstruyendo tabla market core regional...")

market_core = pd.DataFrame()

market_core["country"] = df["country"].fillna(COUNTRY)
market_core["region"] = REGION
market_core["regulator"] = REGULATOR
market_core["source"] = SOURCE

market_core["period_date"] = df["date"]
market_core["year"] = df["year"]
market_core["month"] = df["month"]

market_core["company_local"] = df["company"]
market_core["company_standard"] = df["company"]

market_core["line_of_business_local"] = df["line_of_business"]
market_core["line_of_business_standard"] = df["line_of_business"]

# Colombia tiene este nivel de detalle.
# Para otros países este campo puede quedar vacío o no disponible.
market_core["city"] = df["city"]

# Convertir value_type local a nombres de métricas estándar regionales
metric_mapping = {
    "PRIMAS": "gross_written_premium",
    "SINIESTROS": "claims"
}

market_core["metric_name"] = df["value_type"].map(metric_mapping)
market_core["metric_value"] = df["value"]

market_core["currency"] = CURRENCY
market_core["source_file"] = df["source_file"]
market_core["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Mantener solo métricas reconocidas
market_core = market_core.dropna(subset=["metric_name"])

# Ordenar columnas
market_core = market_core[
    [
        "country",
        "region",
        "regulator",
        "source",
        "period_date",
        "year",
        "month",
        "company_local",
        "company_standard",
        "line_of_business_local",
        "line_of_business_standard",
        "city",
        "metric_name",
        "metric_value",
        "currency",
        "source_file",
        "updated_at"
    ]
]

# ============================================================
# RESULTADOS DE CONTROL
# ============================================================

print("\nTamaño market core:")
print(market_core.shape)

print("\nPrimeras filas:")
print(market_core.head())

print("\nRango de fechas:")
print(market_core["period_date"].min(), "->", market_core["period_date"].max())

print("\nAños disponibles:")
print(sorted(market_core["year"].dropna().unique()))

print("\nMétricas encontradas:")
print(market_core["metric_name"].value_counts())

# ============================================================
# GUARDAR CSV
# ============================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
market_core.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nArchivo market core guardado en:")
print(OUTPUT_FILE)

# ============================================================
# CARGAR A DUCKDB
# ============================================================

print("\nCargando market core a DuckDB...")

conn = duckdb.connect(str(DB_FILE))

conn.execute("""
    CREATE OR REPLACE TABLE fact_market_core AS
    SELECT *
    FROM market_core
""")

summary = conn.execute("""
    SELECT
        country,
        year,
        metric_name,
        COUNT(*) AS records,
        SUM(metric_value) AS total_value
    FROM fact_market_core
    GROUP BY country, year, metric_name
    ORDER BY country, year, metric_name
""").fetchdf()

print("\nResumen cargado en DuckDB:")
print(summary)

total_rows = conn.execute("""
    SELECT COUNT(*) AS total_rows
    FROM fact_market_core
""").fetchdf()

print("\nTotal de registros cargados en fact_market_core:")
print(total_rows)

date_range = conn.execute("""
    SELECT
        MIN(period_date) AS min_date,
        MAX(period_date) AS max_date
    FROM fact_market_core
""").fetchdf()

print("\nRango de fechas en fact_market_core:")
print(date_range)

conn.close()

print("\nProceso completado correctamente.")