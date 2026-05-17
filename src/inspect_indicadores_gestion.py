from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_FOLDER = Path("data/raw/fasecolda")
OUTPUT_FOLDER = Path("outputs/indicadores_gestion_inspection")

# Archivo objetivo: cierre 2025
TARGET_FILE_NAME = "INDICADORES DE GESTION 122025.xls"

# Si el nombre exacto cambia por acento o mayúsculas, buscamos por partes
SEARCH_TERMS = ["INDICADORES", "122025"]

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def safe_text(value):
    """Convierte cualquier valor a texto de forma segura."""
    if pd.isna(value):
        return ""
    return str(value)


def safe_sheet_filename(sheet_name):
    """Convierte el nombre de una hoja en un nombre de archivo seguro."""
    text = safe_text(sheet_name)

    for char in ["/", "\\", ":", "*", "?", "[", "]"]:
        text = text.replace(char, "_")

    text = text.strip()

    if not text:
        text = "sheet"

    return text[:80]


def row_to_text(row):
    """Convierte una fila completa a texto de forma segura."""
    values = [safe_text(v).upper() for v in row.tolist()]
    return " ".join(values)


# ============================================================
# BUSCAR ARCHIVO
# ============================================================

excel_files = []
excel_files.extend(BASE_FOLDER.glob("*.xls"))
excel_files.extend(BASE_FOLDER.glob("*.xlsx"))
excel_files.extend(BASE_FOLDER.glob("**/*.xls"))
excel_files.extend(BASE_FOLDER.glob("**/*.xlsx"))

target_file = None

for file in excel_files:
    name_upper = file.name.upper()
    if file.name == TARGET_FILE_NAME or all(term in name_upper for term in SEARCH_TERMS):
        target_file = file
        break

if target_file is None:
    raise FileNotFoundError(
        "No se encontró el archivo de Indicadores de Gestión 122025. "
        "Verifica que esté en data/raw/fasecolda."
    )

print("Archivo seleccionado:")
print(target_file)

# ============================================================
# INSPECCIONAR HOJAS
# ============================================================

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

xls = pd.ExcelFile(target_file)
sheet_names = xls.sheet_names

print("\nHojas encontradas:")
for sheet in sheet_names:
    print("-", sheet)

summary_rows = []

for sheet in sheet_names:
    print("\n==================================================")
    print("Hoja:", sheet)
    print("==================================================")

    try:
        raw = pd.read_excel(
            target_file,
            sheet_name=sheet,
            header=None
        )

        print("Tamaño completo:")
        print(raw.shape)

        # Guardar preview de primeras 80 filas y 80 columnas
        preview = raw.iloc[:80, :80]

        safe_name = safe_sheet_filename(sheet)
        preview_file = OUTPUT_FOLDER / f"{safe_name}_preview.csv"
        preview.to_csv(preview_file, index=False, header=False, encoding="utf-8-sig")

        # Convertir toda la hoja a texto de forma segura
        text_cells = raw.fillna("").astype(str)
        full_text = text_cells.to_string().upper()

        terms_to_find = [
            "COMPAÑ",
            "ASEGUR",
            "PRIMAS",
            "SINIESTROS",
            "CEDID",
            "REASEGURO",
            "RETENID",
            "RESULTADO",
            "TECNICO",
            "TÉCNICO",
            "GASTOS",
            "COMISION",
            "COMISIÓN",
            "IMPUESTOS",
            "PATRIMONIO",
            "ACTIVO",
            "PASIVO",
            "UTILIDAD",
            "INVERSIONES"
        ]

        detected_terms = [term for term in terms_to_find if term in full_text]

        # Buscar posibles filas de encabezado
        possible_header_rows = []

        max_rows_to_check = min(len(raw), 100)

        for idx in range(max_rows_to_check):
            current_row = raw.iloc[idx]
            row_text = row_to_text(current_row)

            score = 0
            for term in ["COMPAÑ", "PRIMAS", "SINIESTROS", "CEDID", "RESULTADO", "TÉCNICO", "TECNICO"]:
                if term in row_text:
                    score += 1

            non_empty_count = int(current_row.notna().sum())

            if score >= 2 or non_empty_count >= 10:
                possible_header_rows.append({
                    "row_index": idx,
                    "score": score,
                    "non_empty_count": non_empty_count,
                    "row_text_preview": row_text[:300]
                })

        print("Términos detectados:")
        print(detected_terms)

        print("\nPosibles filas de encabezado:")
        for row in possible_header_rows[:10]:
            print(row)

        summary_rows.append({
            "sheet_name": safe_text(sheet),
            "rows": raw.shape[0],
            "columns": raw.shape[1],
            "detected_terms": " | ".join([safe_text(x) for x in detected_terms]),
            "possible_header_rows": str(possible_header_rows[:10]),
            "preview_file": str(preview_file)
        })

    except Exception as e:
        print(f"ERROR inspeccionando hoja {sheet}: {e}")

        summary_rows.append({
            "sheet_name": safe_text(sheet),
            "rows": None,
            "columns": None,
            "detected_terms": f"ERROR: {e}",
            "possible_header_rows": "",
            "preview_file": ""
        })

# ============================================================
# GUARDAR RESUMEN
# ============================================================

summary_df = pd.DataFrame(summary_rows)
summary_file = OUTPUT_FOLDER / "inspection_summary.csv"
summary_df.to_csv(summary_file, index=False, encoding="utf-8-sig")

print("\n==================================================")
print("Inspección completada.")
print("Resumen guardado en:")
print(summary_file)
print("Previews guardados en:")
print(OUTPUT_FOLDER)
print("==================================================")

print("\nResumen:")
print(summary_df[["sheet_name", "rows", "columns", "detected_terms", "preview_file"]])