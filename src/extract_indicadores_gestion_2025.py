from pathlib import Path
from datetime import datetime
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_FOLDER = Path("data/raw/fasecolda")
OUTPUT_FILE = Path("data/processed/indicadores_gestion_2025_core.csv")
ERROR_LOG_FILE = Path("outputs/indicadores_gestion_2025_extraction_errors.csv")

SEARCH_TERMS = ["INDICADORES", "122025"]

COUNTRY = "COLOMBIA"
REGION = "LATIN AMERICA AND CARIBBEAN"
REGULATOR = "FASECOLDA"
SOURCE = "FASECOLDA - INDICADORES DE GESTION"
CURRENCY = "COP"
YEAR = 2025
MONTH = 12
PERIOD_DATE = "2025-12-31"

# Hojas que claramente no queremos procesar como ramos
EXCLUDED_SHEETS = {
    "INDICE",
    "Resumen Balances",
    "BALANCE GENERALES",
    "BALANCE VIDA",
    "Resumen Inversiones",
    "INVERSIONES GENERALES",
    "INVERSIONES VIDA",
    "Resumen Resultados",
    "RESULTADOS GENERALES",
    "RESULTADOS VIDA",
    "Resumen Ramos",
}

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def find_target_file():
    excel_files = []
    excel_files.extend(BASE_FOLDER.glob("*.xls"))
    excel_files.extend(BASE_FOLDER.glob("*.xlsx"))
    excel_files.extend(BASE_FOLDER.glob("**/*.xls"))
    excel_files.extend(BASE_FOLDER.glob("**/*.xlsx"))

    for file in excel_files:
        name_upper = file.name.upper()
        if all(term in name_upper for term in SEARCH_TERMS):
            return file

    raise FileNotFoundError(
        "No se encontró el archivo INDICADORES DE GESTION 122025. "
        "Verifica que esté en data/raw/fasecolda."
    )


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_probable_company(value):
    text = clean_text(value)

    if not text:
        return False

    if text.upper() in ["COMPAÑÍAS", "COMPANIAS", "COMPAÑIA", "COMPAÑÍA"]:
        return False

    if text.upper().startswith("TOTAL"):
        return True

    # Evitar valores que son claramente fechas/números
    try:
        float(text)
        return False
    except ValueError:
        pass

    return len(text) >= 2


def get_numeric(raw, row, col):
    try:
        return pd.to_numeric(raw.iloc[row, col], errors="coerce")
    except Exception:
        return pd.NA


def add_metric(records, sheet_name, company, metric_name, metric_value, source_file):
    if pd.isna(metric_value):
        return

    records.append({
        "country": COUNTRY,
        "region": REGION,
        "regulator": REGULATOR,
        "source": SOURCE,
        "period_date": PERIOD_DATE,
        "year": YEAR,
        "month": MONTH,
        "company_local": company,
        "company_standard": company,
        "line_of_business_local": sheet_name,
        "line_of_business_standard": sheet_name,
        "city": None,
        "metric_name": metric_name,
        "metric_value": float(metric_value),
        "currency": CURRENCY,
        "source_file": source_file,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


def extract_sheet(raw, sheet_name, source_file):
    """
    Extrae métricas principales desde hojas tipo ramo.

    Según la inspección de Transporte:
    - fila 5 contiene bloques de métricas
    - fila 7 contiene fechas
    - filas 9 en adelante contienen compañías
    - col_0 tiene compañía
    - col_2 aprox = Primas emitidas 2025
    - col_6 aprox = Primas retenidas 2025
    - col_10 aprox = % retención 2025

    Importante: estos archivos están en millones de pesos.
    Por eso convertimos a pesos multiplicando por 1,000,000 para mantener consistencia
    con Ciudades y Ramos.
    """

    records = []

    # Validación mínima de tamaño
    if raw.shape[0] < 10 or raw.shape[1] < 12:
        raise ValueError("Hoja demasiado pequeña para estructura esperada.")

    # Validar que parezca hoja de indicadores por compañía
    raw_text = raw.fillna("").astype(str).to_string().upper()

    required_terms = ["COMPAÑ", "PRIMAS", "SINIESTROS"]
    if not all(term in raw_text for term in required_terms):
        raise ValueError("La hoja no parece contener compañías, primas y siniestros.")

    # Columnas tentativas identificadas en la inspección
    company_col = 0

    primas_emitidas_2025_col = 2
    primas_retenidas_2025_col = 6
    retention_ratio_2025_col = 10

    # En la inspección vimos que siniestros pagados aparece más adelante.
    # En muchas hojas está cerca de col_35 / col_36, pero puede variar.
    # Por ahora vamos a intentar detectar automáticamente una columna de SINIESTROS PAGADOS 2025.
    paid_claims_2025_col = None

    # Buscar encabezado "SINIESTROS PAGADOS" en las primeras filas
    for col in range(raw.shape[1]):
        col_text = " ".join(raw.iloc[:8, col].fillna("").astype(str).str.upper().tolist())
        if "SINIESTROS PAGADOS" in col_text:
            # Normalmente el bloque tiene año 2024, año 2025, variación, %
            # Si el título está en la primera columna del bloque, 2025 suele ser col + 1
            paid_claims_2025_col = col + 1
            break

    # Si no se detecta, no bloqueamos extracción
    if paid_claims_2025_col is None:
        paid_claims_2025_col = None

    # Las compañías empiezan normalmente desde fila 9
    for row in range(9, raw.shape[0]):
        company = clean_text(raw.iloc[row, company_col]).upper()

        if not is_probable_company(company):
            continue

        primas_emitidas_2025 = get_numeric(raw, row, primas_emitidas_2025_col)
        primas_retenidas_2025 = get_numeric(raw, row, primas_retenidas_2025_col)
        retention_ratio_2025 = get_numeric(raw, row, retention_ratio_2025_col)

        # Convertir de millones de pesos a pesos
        if not pd.isna(primas_emitidas_2025):
            primas_emitidas_2025 = primas_emitidas_2025 * 1_000_000

        if not pd.isna(primas_retenidas_2025):
            primas_retenidas_2025 = primas_retenidas_2025 * 1_000_000

        add_metric(
            records,
            sheet_name,
            company,
            "gross_written_premium",
            primas_emitidas_2025,
            source_file
        )

        add_metric(
            records,
            sheet_name,
            company,
            "retained_premium",
            primas_retenidas_2025,
            source_file
        )

        add_metric(
            records,
            sheet_name,
            company,
            "retention_ratio",
            retention_ratio_2025,
            source_file
        )

        # Métricas calculadas de cesión
        if not pd.isna(primas_emitidas_2025) and not pd.isna(primas_retenidas_2025):
            ceded_premium = primas_emitidas_2025 - primas_retenidas_2025
            add_metric(
                records,
                sheet_name,
                company,
                "reinsurance_ceded_premium",
                ceded_premium,
                source_file
            )

        if not pd.isna(retention_ratio_2025):
            cession_ratio = 1 - retention_ratio_2025
            add_metric(
                records,
                sheet_name,
                company,
                "reinsurance_cession_ratio",
                cession_ratio,
                source_file
            )

        # Siniestros pagados, si detectamos la columna
        if paid_claims_2025_col is not None and paid_claims_2025_col < raw.shape[1]:
            paid_claims_2025 = get_numeric(raw, row, paid_claims_2025_col)

            if not pd.isna(paid_claims_2025):
                paid_claims_2025 = paid_claims_2025 * 1_000_000

            add_metric(
                records,
                sheet_name,
                company,
                "paid_claims",
                paid_claims_2025,
                source_file
            )

    if not records:
        raise ValueError("No se extrajeron registros de la hoja.")

    return records


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

target_file = find_target_file()

print("Archivo seleccionado:")
print(target_file)

xls = pd.ExcelFile(target_file)
sheet_names = xls.sheet_names

print("\nHojas encontradas:")
for sheet in sheet_names:
    print("-", sheet)

all_records = []
errors = []

for sheet in sheet_names:
    if sheet in EXCLUDED_SHEETS:
        print(f"\nSaltando hoja excluida: {sheet}")
        continue

    print(f"\nProcesando hoja: {sheet}")

    try:
        raw = pd.read_excel(
            target_file,
            sheet_name=sheet,
            header=None
        )

        sheet_records = extract_sheet(raw, sheet, target_file.name)
        all_records.extend(sheet_records)

        print(f"Registros extraídos: {len(sheet_records)}")

    except Exception as e:
        print(f"ERROR en hoja {sheet}: {e}")
        errors.append({
            "sheet_name": sheet,
            "error": str(e)
        })

# ============================================================
# GUARDAR RESULTADOS
# ============================================================

if not all_records:
    raise ValueError("No se extrajo ningún registro de Indicadores de Gestión 2025.")

output_df = pd.DataFrame(all_records)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
output_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

error_df = pd.DataFrame(errors)
ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
error_df.to_csv(ERROR_LOG_FILE, index=False, encoding="utf-8-sig")

print("\n==================================================")
print("Extracción completada.")
print("Archivo limpio guardado en:")
print(OUTPUT_FILE)
print("Log de errores guardado en:")
print(ERROR_LOG_FILE)
print("==================================================")

print("\nTamaño del dataset extraído:")
print(output_df.shape)

print("\nMétricas extraídas:")
print(output_df["metric_name"].value_counts())

print("\nRamos extraídos:")
print(sorted(output_df["line_of_business_standard"].dropna().unique()))

print("\nPrimeras filas:")
print(output_df.head(20))

if not error_df.empty:
    print("\nHojas con errores o no procesadas:")
    print(error_df)