# Data Sources

## Colombia core source target

The Colombia module is migrating its source of truth to:

- Source: Datos Abiertos Colombia / Superintendencia Financiera de Colombia
- Dataset: Informacion estadistica y financiera por ramos de seguros Formato 290
- Dataset ID: `e967-4a8r`
- Endpoint JSON: `https://www.datos.gov.co/resource/e967-4a8r.json`
- Endpoint CSV: `https://www.datos.gov.co/resource/e967-4a8r.csv`
- Metadata endpoint: `https://www.datos.gov.co/api/views/e967-4a8r`

The public metadata confirms the dataset name includes Formato 290, is supplied by the Superintendencia Financiera de Colombia, has monthly update frequency, and reports values in pesos except Unidad de Captura 19 in millions of pesos and Unidad de Captura 20 in units.

## Legacy source

The current demo database may still contain Fasecolda - Ciudades y Ramos data in `fact_market_core`. After the Formato 290 ingestion runs successfully, the app prefers `fact_market_core_formato_290` when that table exists. If it is absent, the app explicitly shows that it is using the legacy Fasecolda snapshot as a fallback.

## Complementary source

Fasecolda - Indicadores de Gestion 2025 remains exploratory for reinsurance discussion signals. It is not the core Colombia market source.

