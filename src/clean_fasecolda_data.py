from pathlib import Path
import pandas as pd

# Archivo combinado que creamos en el paso anterior
input_file = Path("data/processed/fasecolda_2015_2024_combined.csv")

# Archivo limpio que vamos a crear
output_file = Path("data/processed/fasecolda_2015_2024_clean.csv")

print("Leyendo archivo combinado...")
df = pd.read_csv(input_file)

print("Tamaño inicial:")
print(df.shape)

print("Columnas iniciales:")
print(df.columns.tolist())

# Unificar la columna de primas/siniestros.
# Algunos archivos la traen como 'PRIMAS/Siniestros' y otros como 'Primas/Siniestros'
if "PRIMAS/Siniestros" in df.columns and "Primas/Siniestros" in df.columns:
    df["TIPO_VALOR"] = df["PRIMAS/Siniestros"].fillna(df["Primas/Siniestros"])
elif "PRIMAS/Siniestros" in df.columns:
    df["TIPO_VALOR"] = df["PRIMAS/Siniestros"]
elif "Primas/Siniestros" in df.columns:
    df["TIPO_VALOR"] = df["Primas/Siniestros"]
else:
    raise ValueError("No se encontró la columna de primas/siniestros.")

# Crear una tabla con nombres de columnas más fáciles de usar
clean_df = df.rename(columns={
    "COMPAÑÍA": "company",
    "RAMOS": "line_of_business",
    "CIUDAD": "city",
    "VALOR": "value",
    "FECHA": "date",
    "ARCHIVO_FUENTE": "source_file"
})

# Agregar la columna unificada
clean_df["value_type"] = df["TIPO_VALOR"]

# Quedarnos solo con las columnas que necesitamos
clean_df = clean_df[
    [
        "company",
        "value_type",
        "line_of_business",
        "city",
        "value",
        "date",
        "source_file"
    ]
]

# Limpiar textos
text_columns = ["company", "value_type", "line_of_business", "city"]

for col in text_columns:
    clean_df[col] = (
        clean_df[col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

# Convertir fecha
clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")

# Crear columnas de año y mes
clean_df["year"] = clean_df["date"].dt.year
clean_df["month"] = clean_df["date"].dt.month

# Convertir valor a número
clean_df["value"] = pd.to_numeric(clean_df["value"], errors="coerce")

# Quitar registros sin valor o sin fecha
clean_df = clean_df.dropna(subset=["value", "date"])

# Agregar país y fuente
clean_df["country"] = "COLOMBIA"
clean_df["source"] = "FASECOLDA"

print("\nTamaño final limpio:")
print(clean_df.shape)

print("\nPrimeras filas limpias:")
print(clean_df.head())

print("\nColumnas finales:")
print(clean_df.columns.tolist())

print("\nTipos de valor encontrados:")
print(clean_df["value_type"].value_counts())

# Guardar archivo limpio
clean_df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("\nArchivo limpio guardado en:")
print(output_file)