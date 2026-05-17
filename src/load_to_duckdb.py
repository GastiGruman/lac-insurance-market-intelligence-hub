from pathlib import Path
import pandas as pd
import duckdb

# Archivo limpio creado en el paso anterior
input_file = Path("data/processed/fasecolda_2015_2024_clean.csv")

# Ruta donde guardaremos la base de datos
db_file = Path("data/database/insurance_market.duckdb")

print("Leyendo archivo limpio...")
df = pd.read_csv(input_file)

print("Tamaño del dataset:")
print(df.shape)

# Conectar o crear la base DuckDB
print("Creando/conectando base DuckDB...")
conn = duckdb.connect(str(db_file))

# Crear tabla principal
conn.execute("""
    CREATE OR REPLACE TABLE fact_fasecolda_market AS
    SELECT *
    FROM df
""")

# Validar cantidad de registros cargados
result = conn.execute("""
    SELECT COUNT(*) AS total_rows
    FROM fact_fasecolda_market
""").fetchdf()

print("Registros cargados en DuckDB:")
print(result)

# Mostrar primeros registros
preview = conn.execute("""
    SELECT *
    FROM fact_fasecolda_market
    LIMIT 5
""").fetchdf()

print("\nPrimeros registros en la base:")
print(preview)

conn.close()

print("\nBase de datos creada en:")
print(db_file)