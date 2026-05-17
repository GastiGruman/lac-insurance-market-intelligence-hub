# LAC Insurance Market Intelligence Hub — Project Status

## Estado actual

El proyecto ya cuenta con una primera versión funcional del módulo Colombia, construida sobre información pública de Fasecolda.

La herramienta está pensada como una plataforma regional desde el diseño, no como un dashboard exclusivo de Colombia. Colombia funciona como primer país implementado y, por disponibilidad de información, tendrá módulos avanzados adicionales.

Principio de diseño:

**Regional by design. Colombia-rich where possible. Broker-focused always.**

---

## Versión actual

**Versión:** Colombia 1.5 polished internal UI / Phase 5 UI-UX refresh  
**Fecha de actualización del proyecto:** 16/05/2026  
**Última fecha disponible en la base principal:** 31/12/2025  
**Herramienta actual:** Streamlit + Python + pandas + Plotly + DuckDB  
**Base de datos local:** `data/database/insurance_market.duckdb`

---

## Fuentes cargadas

### 1. Fasecolda - Ciudades y Ramos

**Estado:** Core regional principal  
**Uso:** primas, siniestros, siniestralidad, compañías, ramos, ciudades, evolución histórica.  
**Periodo cargado:** 2015-01-31 a 2025-12-31  
**Registros cargados:** 1,293,272  
**Compañías:** 63  
**Ramos:** 26  
**Ciudades:** 36  
**Archivos fuente:** 132

Esta fuente alimenta la tabla principal regional:

`fact_market_core`

También se mantiene una tabla local de Fasecolda:

`fact_fasecolda_market`

Nota metodologica operacional:

- El campo `VALOR` de Ciudades y Ramos se interpreta como miles de COP y se convierte a COP en la capa analitica del app.
- Los archivos mensuales se tratan como cortes acumulados. Para analisis anuales, el app usa el ultimo mes disponible de cada ano en lugar de sumar todos los cortes mensuales.
- Esta correccion evita subestimar las cifras por unidad y evita doble conteo por acumulacion mensual.

---

### 2. Fasecolda - Indicadores de Gestión 2025

**Estado:** Fuente complementaria exploratoria  
**Uso:** primas emitidas, primas retenidas, prima cedida al reaseguro, ratio de cesión, ratio de retención y siniestros pagados.  
**Periodo cargado:** 2025-12-31  
**Registros cargados:** 4,410  
**Compañías:** 66  
**Ramos:** 49  
**Tabla DuckDB:** `fact_indicadores_gestion_2025`

Esta fuente alimenta la pestaña:

`Reinsurance View`

La fuente aún requiere validación metodológica antes de integrarse formalmente al core regional principal. La Reinsurance View usa esta fuente como complemento exploratorio, recalcula ratios a nivel agregado y permite excluir ramos agregados para reducir riesgo de duplicidad.

---

## Tablas principales en DuckDB

### `fact_market_core`

Tabla regional estándar. Actualmente alimentada con Colombia / Fasecolda - Ciudades y Ramos.

Campos principales:

```text
country
region
regulator
source
period_date
year
month
company_local
company_standard
line_of_business_local
line_of_business_standard
city
metric_name
metric_value
currency
source_file
updated_at
```

---

### `fact_indicadores_gestion_2025`

Tabla complementaria exploratoria basada en Fasecolda - Indicadores de Gestión 2025.

Uso actual:

- Reinsurance View.
- Cálculo exploratorio de prima retenida, prima cedida, ratio de retención, ratio de cesión y siniestros pagados.
- Validaciones metodológicas específicas en `src/validate_indicadores_gestion_2025.py`.

Advertencia metodológica:

- Los ratios se recalculan a nivel agregado y no se suman.
- Los ramos agregados como `TOTAL DAÑOS`, `TOTAL PERSONAS` y `TOTAL SEGURIDAD SOCIAL` pueden duplicar ramos individuales.
- La fuente sigue en estado exploratorio hasta completar revisión metodológica más profunda.

---

## Tablas de mapping

Ya existen tablas formales de mapping en DuckDB:

- `dim_line_of_business_mapping`
- `dim_company_mapping`

Estas tablas conectan nombres locales de compañías y ramos entre fuentes públicas con nombres estándar del modelo regional. Esto permite comparar Fasecolda - Ciudades y Ramos con Fasecolda - Indicadores de Gestión sin depender de diccionarios hardcoded dentro de la app.

Estado actual:

- `dim_line_of_business_mapping`: mapping formal de ramos, fuente, país, línea estándar y `lob_group`.
- `dim_company_mapping`: mapping formal de compañías, fuente, país, compañía estándar, grupo y tipo de compañía.
- La Reinsurance View usa estas tablas para mapear filtros de compañía y ramo.
- Los mappings se cargan con `src/load_mappings_to_duckdb.py`.

---

## Reinsurance View

Estado actual:

- Usa `fact_indicadores_gestion_2025` como fuente complementaria exploratoria.
- Usa `dim_line_of_business_mapping` y `dim_company_mapping` para equivalencias entre fuentes.
- Incluye opción `Exclude aggregate lines from rankings`, activada por defecto.
- Excluye ramos con `lob_group = AGGREGATE` y totales como `TOTAL DAÑOS`, `TOTAL PERSONAS` y `TOTAL SEGURIDAD SOCIAL` cuando la opción está activada.
- Muestra notas metodológicas visibles sobre fuente, estado exploratorio, ratios recalculados y riesgo de duplicidad.
- Muestra resumen de validaciones y warning counts sin bloquear la app.

Pendiente:

- Profundizar la validación metodológica antes de integrar Indicadores de Gestión al modelo regional core.
- Confirmar el tratamiento definitivo de ramos agregados y otros ramos potencialmente compuestos.

---

## Validaciones

Validaciones disponibles:

- `src/validate_market_core.py`
- `src/validate_indicadores_gestion_2025.py`
- `src/load_mappings_to_duckdb.py`

La validación de Indicadores de Gestión 2025 genera:

- `outputs/indicadores_gestion_2025_validation_report.csv`
- `outputs/indicadores_gestion_2025_validation_detail.csv`
- `outputs/indicadores_gestion_2025_flags.csv`

Los flags incluyen primas no positivas, primas retenidas mayores a primas emitidas, prima cedida negativa, ratios fuera de rango, siniestros pagados sobre primas mayores a 1, ramos agregados, posible impacto duplicado de agregados y diferencias materiales entre ratios extraídos y calculados.

---

## Phase 2 broker features

Capacidades agregadas:

- Company Brief estructurado con resumen ejecutivo, evolución de primas, siniestralidad, market share, ramos principales, ramos con crecimiento, deterioro técnico, alertas y preguntas sugeridas.
- Company One-Pager dentro del Company Brief, con KPIs, gráficos, alertas técnicas, ángulos de reaseguro y notas metodológicas.
- Exportación de Company Brief en Markdown.
- Exportación de One-Pager en Markdown y HTML.
- Technical Signals ampliado con tabla broker-focused, watchlist, señales de crecimiento, siniestralidad, market share y ratios de cesión exploratorios.
- Reports / Export ampliado con filtered data CSV, annual summary CSV, company summary CSV, reinsurance summary CSV, company brief markdown y one-pager markdown/HTML.

Documentación agregada:

- `docs/data_dictionary.md`
- `docs/methodology.md`

---

## Phase 3 initial AI layer

Capacidades agregadas:

- Nueva pestaña `AI Brief`.
- Detección opcional de configuración AI por variables de entorno.
- Mensaje graceful cuando AI no está configurado: `AI features are not configured yet.`
- `AI Brief` basado solo en contexto estructurado de DuckDB y cálculos del app.
- `Ask the Data` con templates controlados y cálculos seguros en pandas, sin SQL arbitrario.
- `AI Meeting Prep` con propósito, tipo de reunión, observaciones, preguntas, ángulos de reaseguro y caveats cuando AI está configurado.
- Guardrails explícitos contra invención de datos, comparación indebida YTD/full-year, datos privados y asesoría legal/financiera.

Archivos agregados:

- `src/ai_utils.py`
- `src/ai_prompts.py`
- `src/ai_brief.py`
- `docs/ai_module.md`

Variables de entorno soportadas:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`

---

## Phase 4 news module

Capacidades agregadas:

- Nueva pestaña `News`.
- Detección opcional de proveedor de noticias por variables de entorno.
- Mensaje graceful cuando noticias no está configurado: `News module not configured.`
- Company News basado en la compañía seleccionada.
- Market Signals / News para seguros, regulación, reaseguro, señales macro y AI/technology cuando el proveedor las retorna.
- Cada noticia muestra título, fuente, fecha, link, resumen y relevancia broker-focused.
- Caché local en `outputs/news_cache/` para evitar llamadas repetidas en cada refresh.
- Botón de refresh para solicitar noticias nuevas.
- Exportación CSV de noticias de compañía y mercado.
- Resumen AI opcional de noticias cuando AI está configurado.

Archivos agregados:

- `src/news_sources.py`
- `src/news.py`
- `src/news_summary.py`
- `docs/news_module.md`

Variables de entorno soportadas:

- `NEWS_API_KEY`
- `BING_SEARCH_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID`
- `SERPAPI_API_KEY`

Advertencia:

- Las noticias deben verificarse contra la fuente original antes de uso con clientes.
- El módulo evita scraping agresivo y depende de proveedores/API configurados.

---

## Phase 5 UI/UX refresh

Capacidades agregadas:

- Header ejecutivo interno sin logo corporativo.
- Tema profesional con navy, azul, blanco y grises claros.
- Archivo `.streamlit/config.toml`.
- Carpeta `assets/` preparada para futuros activos aprobados.
- Helpers reutilizables en `src/ui_components.py`.
- Sidebar reorganizado por alcance, filtros de portafolio, señales y módulo actual.
- KPI cards estilizadas para primas, siniestros, siniestralidad y registros filtrados.
- Market Overview convertido en landing page ejecutiva con feature cards y acciones clave.
- Company Brief reorganizado como executive broker briefing.
- Data Status rediseñado como panel de gobierno de datos.

Nota:

- No se usa logo corporativo por decisión actual del usuario.
- La actualización es visual y conserva la lógica existente de datos, filtros, gráficos y módulos.
