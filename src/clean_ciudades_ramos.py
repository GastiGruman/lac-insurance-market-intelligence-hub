from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path("data/processed/ciudades_ramos_2015_2025_combined.csv")
OUTPUT_FILE = Path("data/processed/ciudades_ramos_2015_2025_clean.csv")

COUNTRY = "COLOMBIA"
SOURCE = "FASECOLDA"

# ============================================================
# CARGA
# ============================================================

print("Leyendo archivo combinado de Ciudades y Ramos...")
df = pd.read_csv(INPUT_FILE)

print("Tamaño inicial:")
print(df.shape)

print("\nColumnas iniciales:")
print(df.columns.tolist())

# ============================================================
# LIMPIEZA BÁSICA
# ============================================================

# Normalizar nombres de columnas originales
df.columns = [str(col).strip() for col in df.columns]

# Algunas versiones traen dos columnas parecidas:
# "PRIMAS/Siniestros" y "Primas/Siniestros".
# Nos quedamos con la que tenga información.
if "PRIMAS/Siniestros" in df.columns and "Primas/Siniestros" in df.columns:
    df["tipo_valor_original"] = df["PRIMAS/Siniestros"].fillna(df["Primas/Siniestros"])
elif "PRIMAS/Siniestros" in df.columns:
    df["tipo_valor_original"] = df["PRIMAS/Siniestros"]
elif "Primas/Siniestros" in df.columns:
    df["tipo_valor_original"] = df["Primas/Siniestros"]
else:
    raise ValueError("No se encontró columna de Primas/Siniestros.")

required_columns = ["COMPAÑÍA", "RAMOS", "CIUDAD", "VALOR", "FECHA", "ARCHIVO_FUENTE", "tipo_valor_original"]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(f"Faltan columnas requeridas: {missing_columns}")

# Crear dataset limpio
clean_df = pd.DataFrame()

clean_df["company"] = df["COMPAÑÍA"].astype(str).str.strip().str.upper()
clean_df["value_type"] = df["tipo_valor_original"].astype(str).str.strip().str.upper()
clean_df["line_of_business"] = df["RAMOS"].astype(str).str.strip().str.upper()
clean_df["city"] = df["CIUDAD"].astype(str).str.strip().str.upper()

clean_df["value"] = pd.to_numeric(df["VALOR"], errors="coerce")
clean_df["date"] = pd.to_datetime(df["FECHA"], errors="coerce")

clean_df["source_file"] = df["ARCHIVO_FUENTE"].astype(str).str.strip()
clean_df["country"] = COUNTRY
clean_df["source"] = SOURCE

# Año y mes
clean_df["year"] = clean_df["date"].dt.year
clean_df["month"] = clean_df["date"].dt.month

# ============================================================
# NORMALIZACIÓN DE CAMPOS
# ============================================================

# Normalizar value_type
clean_df["value_type"] = clean_df["value_type"].replace({
    "PRIMAS": "PRIMAS",
    "PRIMA": "PRIMAS",
    "SINIESTROS": "SINIESTROS",
    "SINIESTRO": "SINIESTROS"
})

# Eliminar registros claramente inválidos
clean_df = clean_df.dropna(subset=["value", "date", "year", "month"])

# Evitar strings raros creados desde NaN
for col in ["company", "value_type", "line_of_business", "city"]:
    clean_df[col] = clean_df[col].replace({"NAN": None, "NONE": None, "": None})

# Mantener solo tipos de valor reconocidos
clean_df = clean_df[clean_df["value_type"].isin(["PRIMAS", "SINIESTROS"])]

# Convertir año y mes a enteros
clean_df["year"] = clean_df["year"].astype(int)
clean_df["month"] = clean_df["month"].astype(int)

# Ordenar columnas
clean_df = clean_df[
    [
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
]

# ============================================================
# RESULTADOS
# ============================================================

print("\nTamaño final limpio:")
print(clean_df.shape)

print("\nPrimeras filas limpias:")
print(clean_df.head())

print("\nColumnas finales:")
print(clean_df.columns.tolist())

print("\nRango de fechas:")
print(clean_df["date"].min(), "->", clean_df["date"].max())

print("\nAños disponibles:")
print(sorted(clean_df["year"].unique()))

print("\nTipos de valor encontrados:")
print(clean_df["value_type"].value_counts())

# ============================================================
# GUARDAR
# ============================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
clean_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nArchivo limpio guardado en:")
print(OUTPUT_FILE)