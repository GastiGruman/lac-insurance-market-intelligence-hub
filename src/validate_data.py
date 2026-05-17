from pathlib import Path
import pandas as pd
import duckdb

DB_PATH = Path("data/database/insurance_market.duckdb")
OUTPUT_PATH = Path("outputs/data_validation_report.csv")

print("Conectando a DuckDB...")

conn = duckdb.connect(str(DB_PATH))

df = conn.execute("""
    SELECT *
    FROM fact_fasecolda_market
""").fetchdf()

conn.close()

print("Dataset cargado correctamente.")
print("Tamaño del dataset:")
print(df.shape)

validation_results = []

def add_result(test_name, result, detail):
    validation_results.append({
        "test_name": test_name,
        "result": result,
        "detail": detail
    })

# 1. Total de registros
add_result(
    "total_rows",
    "INFO",
    f"{len(df):,} registros"
)

# 2. Años disponibles
years = sorted(df["year"].dropna().unique())
add_result(
    "available_years",
    "INFO",
    f"Años disponibles: {years}"
)

# 3. Tipos de valor
value_types = df["value_type"].value_counts(dropna=False).to_dict()
add_result(
    "value_types",
    "INFO",
    str(value_types)
)

# 4. Valores nulos por columna
nulls = df.isnull().sum()

for column, null_count in nulls.items():
    result = "PASS" if null_count == 0 else "WARNING"
    add_result(
        f"null_values_{column}",
        result,
        f"{null_count:,} valores nulos"
    )

# 5. Valores negativos
negative_values = df[df["value"] < 0]

add_result(
    "negative_values",
    "PASS" if len(negative_values) == 0 else "WARNING",
    f"{len(negative_values):,} registros con valores negativos"
)

# 6. Registros con valor cero
zero_values = df[df["value"] == 0]

add_result(
    "zero_values",
    "INFO",
    f"{len(zero_values):,} registros con valor cero"
)

# 7. Compañías únicas
companies_count = df["company"].nunique()

add_result(
    "unique_companies",
    "INFO",
    f"{companies_count:,} compañías únicas"
)

# 8. Ramos únicos
lines_count = df["line_of_business"].nunique()

add_result(
    "unique_lines_of_business",
    "INFO",
    f"{lines_count:,} ramos únicos"
)

# 9. Ciudades únicas
cities_count = df["city"].nunique()

add_result(
    "unique_cities",
    "INFO",
    f"{cities_count:,} ciudades únicas"
)

# 10. Fechas mínimas y máximas
df["date"] = pd.to_datetime(df["date"], errors="coerce")

min_date = df["date"].min()
max_date = df["date"].max()

add_result(
    "date_range",
    "INFO",
    f"Fecha mínima: {min_date}, Fecha máxima: {max_date}"
)

# 11. Duplicados exactos
duplicate_count = df.duplicated().sum()

add_result(
    "exact_duplicates",
    "PASS" if duplicate_count == 0 else "WARNING",
    f"{duplicate_count:,} duplicados exactos"
)

# 12. Resumen por año y tipo de valor
summary_year_type = (
    df.groupby(["year", "value_type"], as_index=False)["value"]
    .sum()
    .sort_values(["year", "value_type"])
)

print("\nResumen por año y tipo de valor:")
print(summary_year_type)

# Guardar reporte de validación
validation_df = pd.DataFrame(validation_results)
validation_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("\nReporte de validación guardado en:")
print(OUTPUT_PATH)

print("\nResultados de validación:")
print(validation_df)