from datetime import datetime, timezone


CIUDADES_Y_RAMOS_PAGE = "https://www.fasecolda.com/fasecolda/estadisticas-del-sector/ciudades-y-ramos/"
INDICADORES_GESTION_PAGE = "https://www.fasecolda.com/fasecolda/estadisticas-del-sector/indicadores-de-gestion/"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def manual_source_registry() -> list[dict]:
    discovered_at = utc_now_iso()
    return [
        {
            "source_name": "ciudades_y_ramos",
            "display_name": "Fasecolda - Ciudades y Ramos",
            "file_url": "",
            "file_name": "",
            "detected_period": "",
            "file_type": "landing_page",
            "discovered_at": discovered_at,
            "source_page": CIUDADES_Y_RAMOS_PAGE,
            "status": "manual_registry_fallback",
            "expected_pattern": "Primas y siniestros*.xls*",
            "notes": "Official page lists current and historical Ciudades y Ramos downloads.",
        },
        {
            "source_name": "indicadores_gestion",
            "display_name": "Fasecolda - Indicadores de Gestion",
            "file_url": "",
            "file_name": "",
            "detected_period": "",
            "file_type": "landing_page",
            "discovered_at": discovered_at,
            "source_page": INDICADORES_GESTION_PAGE,
            "status": "manual_registry_fallback",
            "expected_pattern": "Indicadores de gestion*.xls*",
            "notes": "Official page lists current and historical Indicadores de Gestion downloads.",
        },
    ]


def configured_source_pages() -> list[dict]:
    return [
        {
            "source_name": "ciudades_y_ramos",
            "display_name": "Fasecolda - Ciudades y Ramos",
            "source_page": CIUDADES_Y_RAMOS_PAGE,
            "keywords": ["ciudades", "ramos", "primas", "siniestros"],
        },
        {
            "source_name": "indicadores_gestion",
            "display_name": "Fasecolda - Indicadores de Gestion",
            "source_page": INDICADORES_GESTION_PAGE,
            "keywords": ["indicadores", "gestion", "gestión"],
        },
    ]

