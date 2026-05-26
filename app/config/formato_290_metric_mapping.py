"""Metric mapping candidates for SFC Formato 290.

The mapping is intentionally transparent: concepts are matched from the official
dataset inventory by normalized keyword rules, then reported as mapped or
pending. Business review is still required before formal use.
"""

FORMATO_290_DATASET_ID = "e967-4a8r"
FORMATO_290_SOURCE_URL = "https://www.datos.gov.co/resource/e967-4a8r.json"
FORMATO_290_METADATA_URL = "https://www.datos.gov.co/api/views/e967-4a8r"
FORMATO_290_SOURCE_NAME = "Datos Abiertos Colombia - SFC Formato 290"

ID_COLUMNS = {
    "a_o",
    "ano",
    "anio",
    "mes",
    "tipo_entidad",
    "codigo_entidad",
    "nombre_entidad",
    "unidad_de_captura",
    "nombre_unidad_de_captura",
    "subcuenta",
    "nombre_subcuenta",
}

METRIC_MAPPING_RULES = {
    "gross_written_premium": [
        ["prima", "emit"],
        ["prima", "exped"],
        ["prima", "direct"],
    ],
    "direct_written_premium": [
        ["prima", "direct"],
    ],
    "accepted_premium": [
        ["prima", "acept"],
        ["coaseguro", "acept"],
        ["reaseguro", "acept"],
    ],
    "ceded_premium": [
        ["prima", "ced"],
        ["reaseguro", "ced"],
    ],
    "retained_premium": [
        ["prima", "reten"],
        ["retencion", "prima"],
    ],
    "earned_premium": [
        ["prima", "deveng"],
        ["prima", "ganad"],
    ],
    "claims_paid": [
        ["siniestro", "pag"],
    ],
    "claims_incurred": [
        ["siniestro", "incurr"],
        ["siniestro", "caus"],
    ],
    "claims_liquidated": [
        ["siniestro", "liquid"],
    ],
    "recoveries_salvage": [
        ["recob"],
        ["salvamento"],
    ],
    "commissions": [
        ["comision"],
    ],
    "intermediary_charges": [
        ["intermediacion"],
        ["intermediario"],
    ],
    "discounts": [
        ["descuento"],
    ],
    "administrative_expenses": [
        ["gasto", "administr"],
    ],
    "technical_result": [
        ["resultado", "tecnico"],
        ["resultado", "ramo"],
    ],
    "technical_reserves": [
        ["reserva", "tecnica"],
    ],
}

LOSS_RATIO_DEFINITION = {
    "preferred_numerator": "claims_incurred",
    "fallback_numerator": "claims_paid",
    "preferred_denominator": "earned_premium",
    "fallback_denominator": "gross_written_premium",
}

