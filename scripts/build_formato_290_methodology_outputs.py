from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data/database/insurance_market.duckdb"
DATA_DICTIONARY_DIR = PROJECT_ROOT / "outputs/data_dictionary"
DATA_QUALITY_DIR = PROJECT_ROOT / "outputs/data_quality"
REFERENCE_DIR = PROJECT_ROOT / "data/reference"
RECONCILIATION_DIR = PROJECT_ROOT / "outputs/reconciliation"


METRIC_METADATA = {
    "direct_written_premium": {
        "category": "Premium Volume",
        "dashboard_metric": "Direct Written Premium",
        "sign": "Positive premium income",
        "basis": "direct",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum by selected period/company/ramo",
        "notes": "UC1 subcuenta 5. Suitable for direct-premium scale once period basis is confirmed.",
    },
    "accepted_premium": {
        "category": "Premium Volume",
        "dashboard_metric": "Accepted Coinsurance Premium",
        "sign": "Positive premium income",
        "basis": "accepted/co-insurance",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC1 subcuenta 10.",
    },
    "accepted_reinsurance_premium": {
        "category": "Premium Volume / Reinsurance",
        "dashboard_metric": "Accepted Reinsurance Premium",
        "sign": "Positive premium income",
        "basis": "accepted reinsurance",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC1 subcuentas 20 and 25.",
    },
    "premium_cancellations": {
        "category": "Premium Volume",
        "dashboard_metric": "Premium Cancellations / Returns",
        "sign": "Restatement / subtractive movement",
        "basis": "premium adjustment",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "Subaccounts explicitly marked as resta in the official instructive.",
    },
    "ceded_premium": {
        "category": "Reinsurance",
        "dashboard_metric": "Ceded Premium",
        "sign": "Subtractive ceded premium movement",
        "basis": "ceded reinsurance",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign; ratios require basis review",
        "notes": "UC1 subcuentas 35 and 40 are marked as resta. Presentation may require absolute value depending on business convention.",
    },
    "retained_premium": {
        "category": "Premium Volume / Reinsurance",
        "dashboard_metric": "Retained Premium",
        "sign": "Subtotal from UC1",
        "basis": "retained",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "use official subtotal if basis is confirmed",
        "notes": "UC1 subcuenta 999. Requires confirmation before comparing with manually reconstructed written/ceded formulas.",
    },
    "earned_premium": {
        "category": "Premium Volume",
        "dashboard_metric": "Earned Premium",
        "sign": "Technical earned premium",
        "basis": "earned",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC3 subcuenta 999 = UC1 + UC2 according to instructive.",
    },
    "technical_reserves": {
        "category": "Claims Performance / Reserves",
        "dashboard_metric": "Technical Reserves Movement",
        "sign": "Signed reserve movement",
        "basis": "reserve movement",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "Contains releases and constitutions; signs are meaningful.",
    },
    "claims_liquidated": {
        "category": "Claims Performance",
        "dashboard_metric": "Liquidated Claims",
        "sign": "Claims cost movement",
        "basis": "gross/accepted claims components",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC5 subtotal. Not the same as final net claims account.",
    },
    "claims_reimbursements": {
        "category": "Claims Performance / Reinsurance",
        "dashboard_metric": "Claims Reimbursements",
        "sign": "Recovering movement",
        "basis": "reinsurance recoveries / reimbursements",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "UC6 includes reinsurance reimbursements. Useful for reinsurance-adjusted analysis after review.",
    },
    "recoveries_salvage": {
        "category": "Claims Performance",
        "dashboard_metric": "Recoveries and Salvage",
        "sign": "Recovering movement with subtractive components",
        "basis": "recoveries/salvage",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "UC7 includes salvage, recobros and related expenses.",
    },
    "claims_incurred": {
        "category": "Claims Performance",
        "dashboard_metric": "Incurred Claims / Company Account",
        "sign": "Signed technical claims account",
        "basis": "net/company account",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "UC8 subtotal = UC4 - UC5 + UC6 + UC7. Can be negative; not ordinary gross siniestralidad.",
    },
    "reinsurance_commissions": {
        "category": "Reinsurance",
        "dashboard_metric": "Reinsurance Commissions / Net Reinsurance Income",
        "sign": "Signed net reinsurance income/expense",
        "basis": "net reinsurance",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "UC9 includes ceded reinsurance commissions and other net reinsurance items.",
    },
    "administrative_expenses": {
        "category": "Expenses and Commissions",
        "dashboard_metric": "Administrative and Personnel Expenses",
        "sign": "Expense movement",
        "basis": "administrative expense",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC11 subtotal.",
    },
    "commissions": {
        "category": "Expenses and Commissions",
        "dashboard_metric": "Commissions",
        "sign": "Expense movement",
        "basis": "commission expense",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC12 subtotal.",
    },
    "technical_result": {
        "category": "Technical Profitability",
        "dashboard_metric": "Technical Result",
        "sign": "Signed result",
        "basis": "technical result",
        "direct": "yes",
        "absolute": "no",
        "aggregation": "sum with sign",
        "notes": "UC14 subtotal = UC3 + UC8 + UC13. Safer than reconstructing combined ratio until all components are approved.",
    },
    "intermediary_charges": {
        "category": "Expenses and Commissions",
        "dashboard_metric": "Intermediary Charges",
        "sign": "Signed charge movement",
        "basis": "intermediation",
        "direct": "with_warning",
        "absolute": "no",
        "aggregation": "sum",
        "notes": "UC27. Requires review before acquisition-cost ratio use.",
    },
}


READINESS_ROWS = [
    {
        "metric_name": "Written Premium",
        "business_question_answered": "How large is the selected company/ramo market on a written premium basis?",
        "formula": "direct_written_premium + accepted_premium + accepted_reinsurance_premium",
        "numerator_concepts": "UC1:005, UC1:010, UC1:020, UC1:025",
        "denominator_concepts": "",
        "gross_or_net_basis": "gross/direct plus accepted",
        "direct_or_retained_basis": "written",
        "source_uc_subcuenta": "1/005; 1/010; 1/020; 1/025",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Written Premium (Direct + Accepted)",
        "recommended_label_spanish": "Prima escrita (directa + aceptada)",
        "notes": "Period basis is cumulative in the period; compare YTD to same month only.",
    },
    {
        "metric_name": "Direct Written Premium",
        "business_question_answered": "How much direct business was written?",
        "formula": "direct_written_premium",
        "numerator_concepts": "UC1:005",
        "denominator_concepts": "",
        "gross_or_net_basis": "gross direct",
        "direct_or_retained_basis": "direct written",
        "source_uc_subcuenta": "1/005",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "yes",
        "requires_business_review": "no",
        "recommended_label_english": "Direct Written Premium",
        "recommended_label_spanish": "Prima emitida directa",
        "notes": "",
    },
    {
        "metric_name": "Accepted Premium",
        "business_question_answered": "How much premium was accepted through co-insurance/reinsurance?",
        "formula": "accepted_premium + accepted_reinsurance_premium",
        "numerator_concepts": "UC1:010; UC1:020; UC1:025",
        "denominator_concepts": "",
        "gross_or_net_basis": "accepted",
        "direct_or_retained_basis": "accepted",
        "source_uc_subcuenta": "1/010; 1/020; 1/025",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "yes",
        "requires_business_review": "no",
        "recommended_label_english": "Accepted Premium",
        "recommended_label_spanish": "Prima aceptada",
        "notes": "",
    },
    {
        "metric_name": "Ceded Premium",
        "business_question_answered": "How much premium was ceded to reinsurance?",
        "formula": "ceded_premium from UC1:035 + UC1:040 or UC21 reinsurance detail",
        "numerator_concepts": "UC1:035; UC1:040; UC21:005-020",
        "denominator_concepts": "",
        "gross_or_net_basis": "ceded",
        "direct_or_retained_basis": "ceded",
        "source_uc_subcuenta": "1/035; 1/040; 21/005; 21/010; 21/015; 21/020",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Ceded Premium",
        "recommended_label_spanish": "Prima cedida",
        "notes": "Ceded subaccounts are marked as resta; presentation convention needs review.",
    },
    {
        "metric_name": "Retained Premium",
        "business_question_answered": "How much premium remains retained after ceded/accepted movements?",
        "formula": "official retained premium subtotal UC1:999",
        "numerator_concepts": "UC1:999",
        "denominator_concepts": "",
        "gross_or_net_basis": "retained",
        "direct_or_retained_basis": "retained",
        "source_uc_subcuenta": "1/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Retained Premium",
        "recommended_label_spanish": "Prima retenida",
        "notes": "Use official subtotal unless reconciliation indicates a different basis is required.",
    },
    {
        "metric_name": "Earned Premium",
        "business_question_answered": "What premium was earned in the technical account?",
        "formula": "earned_premium",
        "numerator_concepts": "UC3:999",
        "denominator_concepts": "",
        "gross_or_net_basis": "earned",
        "direct_or_retained_basis": "earned",
        "source_uc_subcuenta": "3/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "yes",
        "requires_business_review": "no",
        "recommended_label_english": "Earned Premium",
        "recommended_label_spanish": "Prima devengada",
        "notes": "Official instructive states UC3 = UC1 + UC2.",
    },
    {
        "metric_name": "Reinsurance Cession Ratio",
        "business_question_answered": "What share of written premium is ceded to reinsurance?",
        "formula": "abs(ceded_premium) / written_premium",
        "numerator_concepts": "UC1:035 + UC1:040 or UC21 subtotal",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "ceded / written",
        "direct_or_retained_basis": "cession",
        "source_uc_subcuenta": "1/035; 1/040; 21/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Reinsurance Cession Ratio",
        "recommended_label_spanish": "Ratio de cesión al reaseguro",
        "notes": "Formula direction and sign convention require review before formal use.",
    },
    {
        "metric_name": "Retention Ratio",
        "business_question_answered": "What share of written premium is retained?",
        "formula": "retained_premium / written_premium",
        "numerator_concepts": "UC1:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "retained / written",
        "direct_or_retained_basis": "retained",
        "source_uc_subcuenta": "1/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Retention Ratio",
        "recommended_label_spanish": "Ratio de retención",
        "notes": "Use only after retained premium basis is confirmed.",
    },
    {
        "metric_name": "Incurred Claims",
        "business_question_answered": "What is the company-account technical claims movement?",
        "formula": "claims_incurred",
        "numerator_concepts": "UC8:999",
        "denominator_concepts": "",
        "gross_or_net_basis": "net/company account",
        "direct_or_retained_basis": "technical claims account",
        "source_uc_subcuenta": "8/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Incurred Claims / Company Account",
        "recommended_label_spanish": "Siniestros cuenta compañía",
        "notes": "Signed value can be negative; not ordinary gross paid claims.",
    },
    {
        "metric_name": "Incurred Claims / Written Premium",
        "business_question_answered": "How large is the signed technical claims movement relative to written premium?",
        "formula": "claims_incurred / written_premium",
        "numerator_concepts": "UC8:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "technical account / written",
        "direct_or_retained_basis": "written denominator",
        "source_uc_subcuenta": "8/999 over 1/005+010+020+025",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Incurred Claims / Written Premium",
        "recommended_label_spanish": "Siniestros cuenta compañía / prima escrita",
        "notes": "Do not label as plain siniestralidad.",
    },
    {
        "metric_name": "Paid Claims",
        "business_question_answered": "What claims were liquidated/paid-like in the format?",
        "formula": "claims_liquidated",
        "numerator_concepts": "UC5:999",
        "denominator_concepts": "",
        "gross_or_net_basis": "liquidated claims",
        "direct_or_retained_basis": "claims",
        "source_uc_subcuenta": "5/999",
        "available_in_formato_290": "partial",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Liquidated Claims",
        "recommended_label_spanish": "Siniestros liquidados",
        "notes": "Official label is liquidated claims, not necessarily paid claims.",
    },
    {
        "metric_name": "Commission Ratio",
        "business_question_answered": "How large are commission expenses relative to premium?",
        "formula": "commissions / written_premium",
        "numerator_concepts": "UC12:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "expense / written",
        "direct_or_retained_basis": "written denominator",
        "source_uc_subcuenta": "12/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Commission Ratio",
        "recommended_label_spanish": "Ratio de comisiones",
        "notes": "Use after denominator basis is approved.",
    },
    {
        "metric_name": "Intermediary Charges Ratio",
        "business_question_answered": "How material are intermediary charges?",
        "formula": "intermediary_charges / written_premium",
        "numerator_concepts": "UC27:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "expense / written",
        "direct_or_retained_basis": "written denominator",
        "source_uc_subcuenta": "27/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Intermediary Charges Ratio",
        "recommended_label_spanish": "Ratio de cargos de intermediación",
        "notes": "Confirm whether UC26/UC27 belong in acquisition cost analysis.",
    },
    {
        "metric_name": "Acquisition Cost Ratio",
        "business_question_answered": "How large are acquisition-related costs relative to premium?",
        "formula": "(commissions + intermediary_charges) / written_premium",
        "numerator_concepts": "UC12:999 + UC27:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "expense / written",
        "direct_or_retained_basis": "written denominator",
        "source_uc_subcuenta": "12/999; 27/999",
        "available_in_formato_290": "partial",
        "safe_for_dashboard": "no",
        "requires_business_review": "yes",
        "recommended_label_english": "Acquisition Cost Ratio",
        "recommended_label_spanish": "Ratio de costo de adquisición",
        "notes": "Do not show until components are approved.",
    },
    {
        "metric_name": "Administrative Expense Ratio",
        "business_question_answered": "How large are admin/personnel expenses relative to premium?",
        "formula": "administrative_expenses / written_premium",
        "numerator_concepts": "UC11:999",
        "denominator_concepts": "Written Premium",
        "gross_or_net_basis": "expense / written",
        "direct_or_retained_basis": "written denominator",
        "source_uc_subcuenta": "11/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Administrative Expense Ratio",
        "recommended_label_spanish": "Ratio de gastos administrativos",
        "notes": "Use after denominator basis is approved.",
    },
    {
        "metric_name": "Technical Result",
        "business_question_answered": "What technical result does the official format report by ramo?",
        "formula": "technical_result",
        "numerator_concepts": "UC14:999",
        "denominator_concepts": "",
        "gross_or_net_basis": "technical result",
        "direct_or_retained_basis": "technical result",
        "source_uc_subcuenta": "14/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "yes",
        "requires_business_review": "no",
        "recommended_label_english": "Technical Result",
        "recommended_label_spanish": "Resultado técnico",
        "notes": "Safer profitability metric than manually reconstructed combined ratio.",
    },
    {
        "metric_name": "Technical Result Ratio",
        "business_question_answered": "How large is technical result relative to premium?",
        "formula": "technical_result / earned_premium or written_premium",
        "numerator_concepts": "UC14:999",
        "denominator_concepts": "UC3:999 or Written Premium",
        "gross_or_net_basis": "technical result / premium",
        "direct_or_retained_basis": "requires denominator choice",
        "source_uc_subcuenta": "14/999 over 3/999 or written premium",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Technical Result Ratio",
        "recommended_label_spanish": "Margen de resultado técnico",
        "notes": "Denominator must be approved.",
    },
    {
        "metric_name": "Technical Margin",
        "business_question_answered": "What is the technical margin on an approved premium base?",
        "formula": "technical_result / approved premium base",
        "numerator_concepts": "UC14:999",
        "denominator_concepts": "approved premium base",
        "gross_or_net_basis": "technical result / premium",
        "direct_or_retained_basis": "requires review",
        "source_uc_subcuenta": "14/999",
        "available_in_formato_290": "yes",
        "safe_for_dashboard": "with_warning",
        "requires_business_review": "yes",
        "recommended_label_english": "Technical Margin",
        "recommended_label_spanish": "Margen técnico",
        "notes": "Same readiness as technical result ratio.",
    },
    {
        "metric_name": "Combined Ratio",
        "business_question_answered": "What is total claims + expense load relative to premium?",
        "formula": "claims ratio + expense ratio + commission/acquisition ratio",
        "numerator_concepts": "UC8 + UC11 + UC12 + selected acquisition components",
        "denominator_concepts": "approved premium base",
        "gross_or_net_basis": "unclear",
        "direct_or_retained_basis": "requires review",
        "source_uc_subcuenta": "8/999; 11/999; 12/999; optional 27/999",
        "available_in_formato_290": "partial",
        "safe_for_dashboard": "no",
        "requires_business_review": "yes",
        "recommended_label_english": "Combined Ratio",
        "recommended_label_spanish": "Índice combinado",
        "notes": "Do not implement until component inclusion, signs and denominator are approved.",
    },
    {
        "metric_name": "Final Combined Ratio",
        "business_question_answered": "What is final technical cost load including other technical income/expense?",
        "formula": "not approved",
        "numerator_concepts": "would require UC8, UC9, UC10, UC11, UC12, UC13 and other components",
        "denominator_concepts": "approved premium base",
        "gross_or_net_basis": "unclear",
        "direct_or_retained_basis": "requires review",
        "source_uc_subcuenta": "multiple",
        "available_in_formato_290": "partial",
        "safe_for_dashboard": "no",
        "requires_business_review": "yes",
        "recommended_label_english": "Final Combined Ratio",
        "recommended_label_spanish": "Índice combinado final",
        "notes": "Technical Result and Technical Result Ratio are safer alternatives.",
    },
    {
        "metric_name": "Reinsurance-adjusted Combined Ratio",
        "business_question_answered": "How does performance look after reinsurance effects?",
        "formula": "not approved",
        "numerator_concepts": "UC6, UC7, UC9 plus claims/expense components",
        "denominator_concepts": "retained or earned premium base",
        "gross_or_net_basis": "net/retained",
        "direct_or_retained_basis": "requires review",
        "source_uc_subcuenta": "multiple",
        "available_in_formato_290": "partial",
        "safe_for_dashboard": "no",
        "requires_business_review": "yes",
        "recommended_label_english": "Reinsurance-adjusted Combined Ratio",
        "recommended_label_spanish": "Índice combinado ajustado por reaseguro",
        "notes": "Do not implement until reinsurance basis and sign conventions are validated.",
    },
]


def build_concept_methodology_map() -> pd.DataFrame:
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        concepts = conn.execute(
            """
            SELECT
                unidad_de_captura,
                nombre_unidad_de_captura,
                subcuenta,
                nombre_subcuenta,
                metric_name,
                mapping_status,
                unit,
                COUNT(*) AS records,
                SUM(normalized_value) AS total_value
            FROM clean_formato_290
            GROUP BY ALL
            ORDER BY unidad_de_captura, subcuenta, metric_name
            """
        ).fetchdf()
    finally:
        conn.close()

    rows = []
    for _, row in concepts.iterrows():
        meta = METRIC_METADATA.get(row["metric_name"], {})
        rows.append(
            {
                "unidad_de_captura": row["unidad_de_captura"],
                "nombre_unidad_de_captura": row["nombre_unidad_de_captura"],
                "subcuenta": row["subcuenta"],
                "nombre_subcuenta": row["nombre_subcuenta"],
                "metric_category": meta.get("category", "Pending / Other Technical Account"),
                "proposed_dashboard_metric": meta.get("dashboard_metric", "Pending methodology mapping"),
                "sign_convention": meta.get("sign", "Unknown / requires review"),
                "unit": row["unit"],
                "can_be_used_directly": meta.get("direct", "no"),
                "requires_absolute_value_for_presentation": meta.get("absolute", "requires review"),
                "requires_aggregation": meta.get("aggregation", "requires review"),
                "gross_ceded_retained_net_or_unclear": meta.get("basis", "unclear"),
                "notes": meta.get("notes", "Not mapped to a dashboard metric yet."),
                "records": row["records"],
                "total_value": row["total_value"],
            }
        )
    return pd.DataFrame(rows)


def build_technical_bridge() -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = duckdb.connect(str(DB_PATH))
    try:
        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_technical_bridge AS
            WITH bridge AS (
                SELECT
                    period_date,
                    year,
                    month,
                    company_code,
                    company_name_clean,
                    company_display_name,
                    ramo_name_clean,
                    ramo_display_name,
                    SUM(CASE WHEN metric_name = 'direct_written_premium' THEN normalized_value ELSE 0 END) AS direct_written_premium,
                    SUM(CASE WHEN metric_name = 'accepted_premium' THEN normalized_value ELSE 0 END) AS accepted_coinsurance_premium,
                    SUM(CASE WHEN metric_name = 'accepted_reinsurance_premium' THEN normalized_value ELSE 0 END) AS accepted_reinsurance_premium,
                    SUM(CASE WHEN metric_name = 'ceded_premium' THEN normalized_value ELSE 0 END) AS ceded_premium_raw_signed,
                    ABS(SUM(CASE WHEN metric_name = 'ceded_premium' THEN normalized_value ELSE 0 END)) AS ceded_premium_display_abs,
                    SUM(CASE WHEN metric_name = 'retained_premium' THEN normalized_value ELSE 0 END) AS retained_premium,
                    SUM(CASE WHEN metric_name = 'earned_premium' THEN normalized_value ELSE 0 END) AS earned_premium,
                    SUM(CASE WHEN metric_name = 'claims_incurred' THEN normalized_value ELSE 0 END) AS incurred_claims_raw_signed,
                    ABS(SUM(CASE WHEN metric_name = 'claims_incurred' THEN normalized_value ELSE 0 END)) AS incurred_claims_display_abs,
                    SUM(CASE WHEN metric_name = 'claims_liquidated' THEN normalized_value ELSE 0 END) AS liquidated_claims,
                    SUM(CASE WHEN metric_name = 'claims_reimbursements' THEN normalized_value ELSE 0 END) AS claims_reimbursements,
                    SUM(CASE WHEN metric_name = 'recoveries_salvage' THEN normalized_value ELSE 0 END) AS recoveries_salvage,
                    SUM(CASE WHEN metric_name = 'commissions' THEN normalized_value ELSE 0 END) AS commissions_raw_signed,
                    ABS(SUM(CASE WHEN metric_name = 'commissions' THEN normalized_value ELSE 0 END)) AS commissions_display_abs,
                    SUM(CASE WHEN metric_name = 'intermediary_charges' THEN normalized_value ELSE 0 END) AS intermediary_charges_raw_signed,
                    ABS(SUM(CASE WHEN metric_name = 'intermediary_charges' THEN normalized_value ELSE 0 END)) AS intermediary_charges_display_abs,
                    SUM(CASE WHEN metric_name = 'administrative_expenses' THEN normalized_value ELSE 0 END) AS administrative_expenses_raw_signed,
                    ABS(SUM(CASE WHEN metric_name = 'administrative_expenses' THEN normalized_value ELSE 0 END)) AS administrative_expenses_display_abs,
                    SUM(CASE WHEN metric_name = 'discounts' THEN normalized_value ELSE 0 END) AS discounts,
                    SUM(CASE WHEN metric_name = 'reinsurance_commissions' THEN normalized_value ELSE 0 END) AS reinsurance_commissions,
                    SUM(CASE WHEN unidad_de_captura = 13 AND subcuenta = 999 THEN normalized_value ELSE 0 END) AS other_net_technical_items_uc13,
                    SUM(CASE WHEN metric_name = 'technical_result' THEN normalized_value ELSE 0 END) AS official_technical_result_raw
                FROM clean_formato_290
                GROUP BY ALL
            )
            SELECT
                *,
                direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium AS written_premium_dashboard_basis,
                earned_premium + incurred_claims_raw_signed - commissions_display_abs - administrative_expenses_display_abs AS reconstructed_technical_result_candidate_1,
                earned_premium + incurred_claims_raw_signed + other_net_technical_items_uc13 AS reconstructed_technical_result_candidate_2,
                (earned_premium + incurred_claims_raw_signed - commissions_display_abs - administrative_expenses_display_abs) - official_technical_result_raw AS reconstruction_difference_candidate_1,
                (earned_premium + incurred_claims_raw_signed + other_net_technical_items_uc13) - official_technical_result_raw AS reconstruction_difference_candidate_2,
                CASE
                    WHEN official_technical_result_raw = 0 THEN NULL
                    ELSE ((earned_premium + incurred_claims_raw_signed + other_net_technical_items_uc13) - official_technical_result_raw) / ABS(official_technical_result_raw)
                END AS reconstruction_difference_pct_candidate_2,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE incurred_claims_display_abs / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS gross_claims_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE commissions_display_abs / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS commission_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE administrative_expenses_display_abs / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS expense_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE (incurred_claims_display_abs + commissions_display_abs + administrative_expenses_display_abs) / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS indicative_gross_combined_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE official_technical_result_raw / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS technical_result_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE 1 - (official_technical_result_raw / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium))
                END AS implied_combined_ratio_from_technical_result,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE ceded_premium_display_abs / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS reinsurance_cession_ratio_candidate,
                CASE
                    WHEN direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium = 0 THEN NULL
                    ELSE retained_premium / (direct_written_premium + accepted_coinsurance_premium + accepted_reinsurance_premium)
                END AS retention_ratio_candidate
            FROM bridge
            """
        )

        bridge_summary = conn.execute(
            """
            SELECT
                COUNT(*) AS rows,
                SUM(ABS(reconstruction_difference_candidate_2)) AS abs_difference_candidate_2,
                SUM(ABS(official_technical_result_raw)) AS abs_official_technical_result,
                CASE
                    WHEN SUM(ABS(official_technical_result_raw)) = 0 THEN NULL
                    ELSE SUM(ABS(reconstruction_difference_candidate_2)) / SUM(ABS(official_technical_result_raw))
                END AS weighted_difference_pct_candidate_2,
                SUM(CASE WHEN ABS(reconstruction_difference_candidate_2) <= 1 THEN 1 ELSE 0 END) AS near_exact_rows
            FROM mart_formato_290_technical_bridge
            """
        ).fetchdf()

        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_formato_290_combined_ratio_readiness AS
            SELECT * FROM (
                VALUES
                ('Gross Claims Ratio',
                 'abs(incurred_claims_raw_signed) / written_premium_dashboard_basis',
                 'incurred_claims_display_abs',
                 'written_premium_dashboard_basis',
                 'yes',
                 '',
                 'absolute value for business presentation; raw signed preserved',
                 'gross/technical account over written premium',
                 'not a technical result reconstruction',
                 'n/a',
                 'usable with warning',
                 'Show as technical claims ratio, not plain siniestralidad',
                 'Incurred Claims / Written Premium',
                 'Siniestros incurridos / Prima escrita',
                 'Raw UC8 values are signed technical account movements.',
                 'Safe only with explicit warning.'),
                ('Commission Ratio',
                 'abs(commissions_raw_signed) / written_premium_dashboard_basis',
                 'commissions_display_abs',
                 'written_premium_dashboard_basis',
                 'yes',
                 '',
                 'absolute value for business presentation; raw signed preserved',
                 'expense over written premium',
                 'partial',
                 'requires denominator review',
                 'usable with warning',
                 'Methodology Review first',
                 'Commission Ratio',
                 'Ratio de comisiones',
                 'Denominator basis requires approval.',
                 ''),
                ('Expense Ratio',
                 'abs(administrative_expenses_raw_signed) / written_premium_dashboard_basis',
                 'administrative_expenses_display_abs',
                 'written_premium_dashboard_basis',
                 'yes',
                 '',
                 'absolute value for business presentation; raw signed preserved',
                 'expense over written premium',
                 'partial',
                 'requires denominator review',
                 'usable with warning',
                 'Methodology Review first',
                 'Administrative Expense Ratio',
                 'Ratio de gastos administrativos',
                 'Denominator basis requires approval.',
                 ''),
                ('Indicative Gross Combined Ratio',
                 '(abs(incurred_claims_raw_signed) + abs(commissions_raw_signed) + abs(administrative_expenses_raw_signed)) / written_premium_dashboard_basis',
                 'claims + commissions + administrative expenses',
                 'written_premium_dashboard_basis',
                 'partial',
                 'approved acquisition costs, other technical items, denominator basis',
                 'absolute presentation values',
                 'indicative gross/written',
                 'no',
                 'does not reconcile to official technical result',
                 'not safe yet',
                 'Keep hidden outside Methodology Review',
                 'Indicative Gross Combined Ratio',
                 'Índice combinado bruto indicativo',
                 'Not validated against official technical result.',
                 'Candidate 1 is intentionally simple and does not reconcile.'),
                ('Technical Result Ratio',
                 'official_technical_result_raw / written_premium_dashboard_basis',
                 'official_technical_result_raw',
                 'written_premium_dashboard_basis',
                 'yes',
                 'approved denominator basis',
                 'signed technical result',
                 'technical result over written premium',
                 'yes',
                 'official source metric',
                 'usable with warning',
                 'Preferred profitability indicator pending denominator review',
                 'Technical Result Ratio',
                 'Margen de resultado técnico',
                 'Use official technical result; denominator requires approval.',
                 ''),
                ('Implied Combined Ratio from Technical Result',
                 '1 - (official_technical_result_raw / written_premium_dashboard_basis)',
                 'official_technical_result_raw',
                 'written_premium_dashboard_basis',
                 'yes',
                 'approved denominator and interpretation',
                 'signed technical result',
                 'implied profitability proxy',
                 'yes',
                 'uses official technical result but not a component combined ratio',
                 'usable with warning',
                 'Do not label as validated combined ratio',
                 'Implied Ratio from Technical Result',
                 'Ratio implícito desde resultado técnico',
                 'This is an implied proxy, not a reconstructed combined ratio.',
                 ''),
                ('Reinsurance Cession Ratio',
                 'abs(ceded_premium_raw_signed) / written_premium_dashboard_basis',
                 'ceded_premium_display_abs',
                 'written_premium_dashboard_basis',
                 'yes',
                 'approved ceded numerator source between UC1 and UC21',
                 'absolute ceded amount for business presentation',
                 'ceded over written premium',
                 'not a technical result reconstruction',
                 'basis review required',
                 'usable with warning',
                 'Methodology Review first',
                 'Reinsurance Cession Ratio',
                 'Ratio de cesión al reaseguro',
                 'Choose UC1 or UC21 basis before formal use.',
                 ''),
                ('Retention Ratio',
                 'retained_premium / written_premium_dashboard_basis',
                 'retained_premium',
                 'written_premium_dashboard_basis',
                 'yes',
                 'approved retained premium basis',
                 'source signed subtotal',
                 'retained over written premium',
                 'not a technical result reconstruction',
                 'basis review required',
                 'usable with warning',
                 'Methodology Review first',
                 'Retention Ratio',
                 'Ratio de retención',
                 'Use only after retained premium basis is approved.',
                 ''),
                ('Net / Retained Combined Ratio',
                 'not approved',
                 'net claims + expenses + reinsurance effects',
                 'retained or earned premium',
                 'partial',
                 'compatible net claims, expense and reinsurance basis',
                 'unclear',
                 'net/retained',
                 'no',
                 'not tested',
                 'not safe yet',
                 'Keep hidden',
                 'Net / Retained Combined Ratio',
                 'Índice combinado neto / retenido',
                 'Components are not yet methodologically aligned.',
                 '')
            ) AS t(
                ratio_name,
                formula,
                numerator_components,
                denominator,
                components_available,
                components_missing,
                sign_handling,
                gross_or_net_basis,
                reconciles_to_technical_result,
                reconciliation_quality,
                readiness_status,
                recommended_dashboard_use,
                recommended_label_english,
                recommended_label_spanish,
                warning_message,
                notes
            )
            """
        )

        readiness = conn.execute("SELECT * FROM mart_formato_290_combined_ratio_readiness").fetchdf()

        latest_period = conn.execute("SELECT MAX(period_date) FROM mart_formato_290_technical_bridge").fetchone()[0]
        top_company_rows = conn.execute(
            """
            WITH top_companies AS (
                SELECT company_code
                FROM mart_formato_290_technical_bridge
                WHERE period_date = ?
                GROUP BY company_code
                ORDER BY SUM(written_premium_dashboard_basis) DESC
                LIMIT 10
            ),
            top_ramos AS (
                SELECT ramo_name_clean
                FROM mart_formato_290_technical_bridge
                WHERE period_date = ?
                GROUP BY ramo_name_clean
                ORDER BY SUM(written_premium_dashboard_basis) DESC
                LIMIT 10
            )
            SELECT
                company_display_name,
                ramo_display_name,
                period_date,
                written_premium_dashboard_basis,
                ceded_premium_raw_signed,
                ceded_premium_display_abs,
                retained_premium,
                incurred_claims_raw_signed,
                incurred_claims_display_abs,
                commissions_raw_signed,
                commissions_display_abs,
                administrative_expenses_raw_signed,
                administrative_expenses_display_abs,
                reinsurance_commissions,
                claims_reimbursements,
                recoveries_salvage,
                official_technical_result_raw,
                reconstructed_technical_result_candidate_1,
                reconstructed_technical_result_candidate_2,
                reconstruction_difference_candidate_1,
                reconstruction_difference_candidate_2,
                reconstruction_difference_pct_candidate_2,
                CASE
                    WHEN ABS(reconstruction_difference_candidate_2) <= 1 THEN 'Candidate 2 reconciles to official technical result.'
                    ELSE 'Review difference against official technical result.'
                END AS comments
            FROM mart_formato_290_technical_bridge
            WHERE period_date = ?
              AND (company_code IN (SELECT company_code FROM top_companies)
                   OR ramo_name_clean IN (SELECT ramo_name_clean FROM top_ramos)
                   OR incurred_claims_raw_signed < 0)
            ORDER BY written_premium_dashboard_basis DESC
            LIMIT 250
            """,
            [latest_period, latest_period, latest_period],
        ).fetchdf()
    finally:
        conn.close()

    return bridge_summary, readiness, top_company_rows


def main() -> int:
    DATA_DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    RECONCILIATION_DIR.mkdir(parents=True, exist_ok=True)

    concept_map = build_concept_methodology_map()
    concept_map.to_csv(
        DATA_DICTIONARY_DIR / "formato_290_metric_methodology_map.csv",
        index=False,
        encoding="utf-8-sig",
    )

    readiness = pd.DataFrame(READINESS_ROWS)
    readiness.to_csv(
        DATA_QUALITY_DIR / "formato_290_metric_readiness_matrix.csv",
        index=False,
        encoding="utf-8-sig",
    )

    template = pd.DataFrame(
        columns=[
            "validation_case_id",
            "source",
            "period",
            "year",
            "month_cutoff",
            "company_code",
            "company_name",
            "ramo",
            "metric_name",
            "official_value",
            "dashboard_value",
            "difference",
            "percentage_difference",
            "tolerance",
            "status",
            "comments",
        ]
    )
    template.to_csv(
        REFERENCE_DIR / "formato_290_reconciliation_template.csv",
        index=False,
        encoding="utf-8-sig",
    )

    bridge_summary, combined_readiness, sample = build_technical_bridge()
    combined_readiness.to_csv(
        DATA_QUALITY_DIR / "formato_290_combined_ratio_readiness.csv",
        index=False,
        encoding="utf-8-sig",
    )
    sample.to_csv(
        RECONCILIATION_DIR / "formato_290_technical_bridge_sample.csv",
        index=False,
        encoding="utf-8-sig",
    )
    bridge_summary.to_csv(
        DATA_QUALITY_DIR / "formato_290_technical_bridge_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Wrote {len(concept_map):,} concept methodology rows.")
    print(f"Wrote {len(readiness):,} metric readiness rows.")
    print(f"Wrote {len(combined_readiness):,} combined ratio readiness rows.")
    print(f"Wrote {len(sample):,} technical bridge sample rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
