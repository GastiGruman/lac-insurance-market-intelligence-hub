from pathlib import Path
import pandas as pd

# Carpeta donde están los archivos de Fasecolda
BASE_FOLDER = Path("data/raw/fasecolda")

# Archivo de salida con el inventario de fuentes
OUTPUT_FILE = Path("outputs/fasecolda_sources_inventory.csv")

# Buscar archivos Excel dentro de data/raw/fasecolda y subcarpetas
excel_files = []
excel_files.extend(BASE_FOLDER.glob("*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("*.xls"))
excel_files.extend(BASE_FOLDER.glob("*.xlsm"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("**/*.xls"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsm"))

# Quitar duplicados
excel_files = sorted(list(set(excel_files)))

print("Archivos Excel encontrados:", len(excel_files))

inventory = []

for file in excel_files:
    print("\n==================================================")
    print("Archivo:", file)
    print("==================================================")

    try:
        xls = pd.ExcelFile(file)
        sheet_names = xls.sheet_names

        print("Hojas encontradas:", sheet_names)

        for sheet in sheet_names:
            try:
                # Leer solo algunas filas para explorar estructura
                preview = pd.read_excel(file, sheet_name=sheet, nrows=20)

                rows_preview = preview.shape[0]
                cols_preview = preview.shape[1]
                columns = [str(c) for c in preview.columns.tolist()]

                print(f"\nHoja: {sheet}")
                print("Tamaño preview:", preview.shape)
                print("Columnas:", columns)

                inventory.append({
                    "file_name": file.name,
                    "file_path": str(file),
                    "sheet_name": sheet,
                    "preview_rows": rows_preview,
                    "preview_columns": cols_preview,
                    "columns": " | ".join(columns)
                })

            except Exception as sheet_error:
                print(f"Error leyendo hoja {sheet}: {sheet_error}")

                inventory.append({
                    "file_name": file.name,
                    "file_path": str(file),
                    "sheet_name": sheet,
                    "preview_rows": None,
                    "preview_columns": None,
                    "columns": f"ERROR: {sheet_error}"
                })

    except Exception as file_error:
        print(f"Error leyendo archivo {file.name}: {file_error}")

        inventory.append({
            "file_name": file.name,
            "file_path": str(file),
            "sheet_name": None,
            "preview_rows": None,
            "preview_columns": None,
            "columns": f"ERROR: {file_error}"
        })

inventory_df = pd.DataFrame(inventory)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
inventory_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n==================================================")
print("Inventario generado en:")
print(OUTPUT_FILE)
print("==================================================")

print("\nResumen del inventario:")
print(inventory_df[["file_name", "sheet_name", "preview_columns"]].head(50))