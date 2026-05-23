from pathlib import Path
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_FILE = Path("data/database/insurance_market.duckdb")
OUTPUT_FILE = Path("outputs/market_core_validation_report.csv")

TABLE_NAME = "fact_market_core"

# ============================================================
# CARGA DESDE DUCKDB
# ============================================================

print("Conectando a DuckDB...")

conn = duckdb.connect(str(DB_FILE))

df = conn.execute(f"""
    SELECT *
    FROM {TABLE_NAME}
""").fetchdf()

conn.close()

print("Market Core cargado correctamente.")
print("Tamaño del dataset:")
print(df.shape)

# ============================================================
# VALIDACIONES
# ============================================================

validation_results = []

def add_result(test_name, result, detail):
    validation_results.append({
        "test_name": test_name,
        "result": result,
        "detail": detail
    })

# Normalizar tipos
df["period_date"] = pd.to_datetime(df["period_date"], errors="coerce")
df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["month"] = pd.to_numeric(df["month"], errors="coerce")

# 1. Total de registros
add_result(
    "total_rows",
    "INFO",
    f"{len(df):,} registros"
)

# 2. Rango de fechas
min_date = df["period_date"].min()
max_date = df["period_date"].max()

add_result(
    "date_range",
    "INFO",
    f"Fecha mínima: {min_date}, Fecha máxima: {max_date}"
)

# 3. Años disponibles
years = sorted(df["year"].dropna().astype(int).unique())

add_result(
    "available_years",
    "INFO",
    f"Años disponibles: {years}"
)

# 4. Países disponibles
countries = sorted(df["country"].dropna().unique())

add_result(
    "available_countries",
    "INFO",
    f"Países disponibles: {countries}"
)

# 5. Métricas disponibles
metrics = df["metric_name"].value_counts(dropna=False).to_dict()

add_result(
    "available_metrics",
    "INFO",
    str(metrics)
)

# 6. Valores nulos por columna
nulls = df.isnull().sum()

for column, null_count in nulls.items():
    result = "PASS" if null_count == 0 else "WARNING"
    add_result(
        f"null_values_{column}",
        result,
        f"{null_count:,} valores nulos"
    )

# 7. Valores negativos
negative_values = df[df["metric_value"] < 0]

add_result(
    "negative_metric_values",
    "PASS" if len(negative_values) == 0 else "WARNING",
    f"{len(negative_values):,} registros con valores negativos"
)

# 8. Valores cero
zero_values = df[df["metric_value"] == 0]

add_result(
    "zero_metric_values",
    "INFO",
    f"{len(zero_values):,} registros con valor cero"
)

# 9. Duplicados exactos
duplicate_count = df.duplicated().sum()

add_result(
    "exact_duplicates",
    "PASS" if duplicate_count == 0 else "WARNING",
    f"{duplicate_count:,} duplicados exactos"
)

# 10. Conteo de compañías, ramos, ciudades y archivos
add_result(
    "unique_companies",
    "INFO",
    f"{df['company_standard'].nunique():,} compañías únicas"
)

add_result(
    "unique_lines_of_business",
    "INFO",
    f"{df['line_of_business_standard'].nunique():,} ramos únicos"
)

add_result(
    "unique_cities",
    "INFO",
    f"{df['city'].nunique():,} ciudades únicas"
)

add_result(
    "unique_source_files",
    "INFO",
    f"{df['source_file'].nunique():,} archivos fuente únicos"
)

# 11. Resumen por año y métrica
summary_year_metric = (
    df.groupby(["country", "year", "metric_name"], as_index=False)["metric_value"]
    .sum()
    .sort_values(["country", "year", "metric_name"])
)

print("\nResumen por año y métrica:")
print(summary_year_metric)

# 12. Validación básica del ratio analítico siniestros / primas por año
premium = (
    df[df["metric_name"] == "gross_written_premium"]
    .groupby(["country", "year"], as_index=False)["metric_value"]
    .sum()
    .rename(columns={"metric_value": "premium"})
)

claims = (
    df[df["metric_name"] == "claims"]
    .groupby(["country", "year"], as_index=False)["metric_value"]
    .sum()
    .rename(columns={"metric_value": "claims"})
)

loss_ratio = premium.merge(claims, on=["country", "year"], how="left")
loss_ratio["claims"] = loss_ratio["claims"].fillna(0)
loss_ratio["loss_ratio"] = loss_ratio["claims"] / loss_ratio["premium"]

print("\nRatio analítico siniestros / primas por año:")
print(loss_ratio)

high_loss_ratio = loss_ratio[loss_ratio["loss_ratio"] > 1]

add_result(
    "annual_claims_premiums_ratio_above_100",
    "PASS" if len(high_loss_ratio) == 0 else "WARNING",
    f"{len(high_loss_ratio):,} años con ratio analítico siniestros / primas superior a 100%"
)

# ============================================================
# GUARDAR REPORTE
# ============================================================

validation_df = pd.DataFrame(validation_results)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
validation_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nReporte de validación guardado en:")
print(OUTPUT_FILE)

print("\nResultados de validación:")
print(validation_df)

print("\nValidación completada correctamente.")
