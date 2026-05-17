from pathlib import Path
import pandas as pd
import duckdb

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_FILE = Path("data/database/insurance_market.duckdb")
OUTPUT_FILE = Path("outputs/company_names_inventory.csv")

# ============================================================
# CARGA DESDE DUCKDB
# ============================================================

print("Conectando a DuckDB...")

conn = duckdb.connect(str(DB_FILE))

market_core = conn.execute("""
    SELECT DISTINCT
        country,
        source,
        company_standard AS company_name
    FROM fact_market_core
    WHERE company_standard IS NOT NULL
""").fetchdf()

try:
    indicadores = conn.execute("""
        SELECT DISTINCT
            country,
            source,
            company_standard AS company_name
        FROM fact_indicadores_gestion_2025
        WHERE company_standard IS NOT NULL
    """).fetchdf()
except Exception as e:
    print(f"No se pudo leer fact_indicadores_gestion_2025: {e}")
    indicadores = pd.DataFrame(columns=["country", "source", "company_name"])

conn.close()

# ============================================================
# COMBINAR E INVENTARIAR
# ============================================================

inventory = pd.concat([market_core, indicadores], ignore_index=True)

inventory["country"] = inventory["country"].astype(str).str.strip().str.upper()
inventory["source"] = inventory["source"].astype(str).str.strip()
inventory["company_name"] = inventory["company_name"].astype(str).str.strip()
inventory["company_name_norm"] = inventory["company_name"].str.upper()

inventory = inventory.drop_duplicates()

print("\nTamaño del inventario:")
print(inventory.shape)

print("\nResumen por fuente:")
summary = (
    inventory
    .groupby(["country", "source"], as_index=False)
    .agg(
        unique_companies=("company_name", "nunique")
    )
)

print(summary)

# ============================================================
# COMPARAR FUENTES
# ============================================================

market_companies = set(
    inventory[
        inventory["source"].str.upper().str.contains("CIUDADES Y RAMOS", na=False)
    ]["company_name_norm"]
)

indicadores_companies = set(
    inventory[
        inventory["source"].str.upper().str.contains("INDICADORES", na=False)
    ]["company_name_norm"]
)

only_market = sorted(market_companies - indicadores_companies)
only_indicadores = sorted(indicadores_companies - market_companies)
in_both = sorted(market_companies & indicadores_companies)

print("\nCompañías en ambas fuentes:")
print(len(in_both))
print(in_both[:100])

print("\nSolo en Ciudades y Ramos:")
print(len(only_market))
print(only_market[:100])

print("\nSolo en Indicadores de Gestión:")
print(len(only_indicadores))
print(only_indicadores[:100])

# ============================================================
# GUARDAR INVENTARIO DETALLADO
# ============================================================

inventory["in_market_core"] = inventory["company_name_norm"].isin(market_companies)
inventory["in_indicadores_gestion"] = inventory["company_name_norm"].isin(indicadores_companies)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
inventory.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nInventario de compañías guardado en:")
print(OUTPUT_FILE)

print("\nPrimeras filas:")
print(inventory.head(50))

print("\nInspección completada correctamente.")