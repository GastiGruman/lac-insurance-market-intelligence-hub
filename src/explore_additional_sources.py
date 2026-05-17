from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_FOLDER = Path("data/raw/fasecolda")
OUTPUT_FILE = Path("outputs/additional_sources_inventory.csv")

KEYWORDS = [
    "INDICADORES",
    "GESTION",
    "GESTIÓN",
    "PRINCIPALES",
    "CIFRAS"
]

# ============================================================
# BUSCAR ARCHIVOS RELEVANTES
# ============================================================

excel_files = []
excel_files.extend(BASE_FOLDER.glob("*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("*.xls"))
excel_files.extend(BASE_FOLDER.glob("*.xlsm"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("**/*.xls"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsm"))

excel_files = sorted(list(set(excel_files)))

target_files = [
    file for file in excel_files
    if any(keyword in file.name.upper() for keyword in KEYWORDS)
]

print("Archivos adicionales encontrados:")
print(len(target_files))

for file in target_files:
    print("-", file.name)

# ============================================================
# EXPLORAR ARCHIVOS
# ============================================================

inventory = []

for file in target_files:
    print("\n==================================================")
    print("Archivo:", file.name)
    print("Ruta:", file)
    print("==================================================")

    try:
        xls = pd.ExcelFile(file)
        sheet_names = xls.sheet_names

        print("Hojas:", sheet_names)

        for sheet in sheet_names:
            try:
                # Leer preview sin asumir encabezado
                raw_preview = pd.read_excel(
                    file,
                    sheet_name=sheet,
                    header=None,
                    nrows=25
                )

                # Leer preview normal
                normal_preview = pd.read_excel(
                    file,
                    sheet_name=sheet,
                    nrows=25
                )

                print(f"\nHoja: {sheet}")
                print("Tamaño raw preview:", raw_preview.shape)
                print("Tamaño normal preview:", normal_preview.shape)
                print("Columnas normal:", [str(c) for c in normal_preview.columns.tolist()])

                # Buscar palabras clave dentro del preview crudo
                raw_text = raw_preview.astype(str).to_string().upper()

                detected_terms = []
                for term in [
                    "PRIMAS",
                    "SINIESTROS",
                    "REASEGURO",
                    "CEDID",
                    "RESULTADO",
                    "TECNICO",
                    "TÉCNICO",
                    "NETO",
                    "COMISION",
                    "COMISIÓN",
                    "GASTOS",
                    "IMPUESTOS",
                    "PATRIMONIO",
                    "ACTIVO",
                    "PASIVO",
                    "UTILIDAD",
                    "INVERSIONES"
                ]:
                    if term in raw_text:
                        detected_terms.append(term)

                inventory.append({
                    "file_name": file.name,
                    "file_path": str(file),
                    "sheet_name": sheet,
                    "raw_rows_preview": raw_preview.shape[0],
                    "raw_columns_preview": raw_preview.shape[1],
                    "normal_columns_preview": normal_preview.shape[1],
                    "normal_columns": " | ".join([str(c) for c in normal_preview.columns.tolist()]),
                    "detected_terms": " | ".join(detected_terms)
                })

            except Exception as sheet_error:
                print(f"Error leyendo hoja {sheet}: {sheet_error}")

                inventory.append({
                    "file_name": file.name,
                    "file_path": str(file),
                    "sheet_name": sheet,
                    "raw_rows_preview": None,
                    "raw_columns_preview": None,
                    "normal_columns_preview": None,
                    "normal_columns": f"ERROR: {sheet_error}",
                    "detected_terms": ""
                })

    except Exception as file_error:
        print(f"Error leyendo archivo {file.name}: {file_error}")

        inventory.append({
            "file_name": file.name,
            "file_path": str(file),
            "sheet_name": None,
            "raw_rows_preview": None,
            "raw_columns_preview": None,
            "normal_columns_preview": None,
            "normal_columns": f"ERROR: {file_error}",
            "detected_terms": ""
        })

# ============================================================
# GUARDAR INVENTARIO
# ============================================================

inventory_df = pd.DataFrame(inventory)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
inventory_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n==================================================")
print("Inventario generado en:")
print(OUTPUT_FILE)
print("==================================================")

print("\nResumen:")
if not inventory_df.empty:
    print(inventory_df[["file_name", "sheet_name", "normal_columns_preview", "detected_terms"]].head(100))
else:
    print("No se encontraron archivos adicionales.")