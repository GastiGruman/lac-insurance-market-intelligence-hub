from pathlib import Path
import pandas as pd

BASE_FOLDER = Path("data/raw/fasecolda")
OUTPUT_FILE = Path("outputs/indicadores_gestion_transporte_detailed_preview.csv")

SEARCH_TERMS = ["INDICADORES", "122025"]
SHEET_NAME = "Transporte"

excel_files = []
excel_files.extend(BASE_FOLDER.glob("*.xls"))
excel_files.extend(BASE_FOLDER.glob("*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("**/*.xls"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsx"))

target_file = None

for file in excel_files:
    name_upper = file.name.upper()
    if all(term in name_upper for term in SEARCH_TERMS):
        target_file = file
        break

if target_file is None:
    raise FileNotFoundError("No se encontró el archivo INDICADORES DE GESTION 122025.")

print("Archivo seleccionado:")
print(target_file)

raw = pd.read_excel(
    target_file,
    sheet_name=SHEET_NAME,
    header=None
)

print("\nTamaño de la hoja:")
print(raw.shape)

# Tomar una muestra amplia
preview = raw.iloc[:40, :40].copy()

# Agregar índice de fila como primera columna
preview.insert(0, "row_index", preview.index)

# Renombrar columnas con índice para facilitar lectura
new_columns = ["row_index"]

for i in range(preview.shape[1] - 1):
    new_columns.append(f"col_{i}")

preview.columns = new_columns

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
preview.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\nPreview detallado guardado en:")
print(OUTPUT_FILE)

print("\nPrimeras 40 filas x 40 columnas de la hoja Transporte:")
pd.set_option("display.max_rows", 50)
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 300)

print(preview)