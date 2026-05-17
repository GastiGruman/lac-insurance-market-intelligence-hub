from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_FOLDER = Path("data/raw/fasecolda")
OUTPUT_FILE = Path("data/processed/ciudades_ramos_2015_2025_combined.csv")

# Buscar únicamente archivos de Ciudades y Ramos
excel_files = []
excel_files.extend(BASE_FOLDER.glob("*Ciudades y Ramos*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("*Ciudades y Ramos*.xls"))
excel_files.extend(BASE_FOLDER.glob("**/*Ciudades y Ramos*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("**/*Ciudades y Ramos*.xls"))

excel_files = sorted(list(set(excel_files)))

print("Archivos de Ciudades y Ramos encontrados:")
print(len(excel_files))

for file in excel_files[:20]:
    print("-", file.name)

if len(excel_files) > 20:
    print(f"... y {len(excel_files) - 20} archivos más")

# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================

all_data = []

for file in excel_files:
    print(f"Leyendo: {file.name}")

    try:
        # En los archivos que ya usamos, la hoja Base tenía la estructura limpia
        df = pd.read_excel(file, sheet_name="Base")

        # Normalizar nombres de columnas
        df.columns = [str(col).strip() for col in df.columns]

        # Agregar archivo fuente
        df["ARCHIVO_FUENTE"] = file.name

        all_data.append(df)

    except Exception as e:
        print(f"ERROR leyendo {file.name}: {e}")

# ============================================================
# COMBINAR
# ============================================================

if not all_data:
    raise ValueError("No se pudo leer ningún archivo de Ciudades y Ramos.")

combined_df = pd.concat(all_data, ignore_index=True)

print("\nTamaño final combinado:")
print(combined_df.shape)

print("\nPrimeras filas:")
print(combined_df.head())

print("\nColumnas:")
print(combined_df.columns.tolist())

# ============================================================
# GUARDAR
# ============================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
combined_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nArchivo combinado guardado en:")
print(OUTPUT_FILE)