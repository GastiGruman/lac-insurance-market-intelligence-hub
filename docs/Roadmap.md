# Roadmap — Colombia Insurance Market Intelligence

## Objetivo general

Convertir el MVP actual en una plataforma interna robusta de inteligencia de mercado asegurador, empezando por Colombia y con potencial de expansión regional hacia otros países de Latinoamérica.

---

## Fase 1 — MVP Colombia

**Estado:** completado en versión inicial.

### Incluye

- Consolidación de archivos públicos de Fasecolda.
- Limpieza inicial de datos.
- Carga en base local DuckDB.
- Dashboard interactivo en Streamlit.
- Filtros por año, compañía, ramo y ciudad.
- KPIs de primas, siniestros y siniestralidad.
- Market Overview.
- Company Explorer.
- Line of Business Explorer.
- Technical Signals.
- Data Table descargable.

### Objetivo de esta fase

Demostrar que la información pública puede transformarse en una herramienta práctica para brokers.

---

## Fase 2 — Validación de datos

**Prioridad:** alta.

### Tareas

- Validar cifras totales contra los archivos originales de Fasecolda.
- Confirmar si las cifras están en pesos, miles de pesos o millones de pesos.
- Confirmar si la información es mensual, acumulada o anual.
- Revisar duplicados.
- Revisar registros vacíos.
- Revisar compañías con nombres inconsistentes.
- Revisar ramos con nombres inconsistentes.
- Documentar la metodología de limpieza.
- Crear una tabla de control de calidad.

### Entregable esperado

Una versión validada del dataset, con metodología clara y controles básicos de calidad.

---

## Fase 3 — Mejora analítica

**Prioridad:** alta.

### Tareas

- Agregar crecimiento anual por compañía.
- Agregar crecimiento anual por ramo.
- Agregar market share por compañía y por ramo.
- Agregar comparación compañía vs mercado.
- Agregar ranking de mejora/deterioro de siniestralidad.
- Agregar filtros de tamaño mínimo de primas para evitar señales distorsionadas.
- Agregar análisis de concentración de mercado.
- Agregar comparaciones entre compañías.

### Entregable esperado

Un dashboard más útil para preparación de reuniones y análisis técnico-comercial.

---

## Fase 4 — Automatización

**Prioridad:** media-alta.

### Tareas

- Automatizar descarga de archivos desde fuentes públicas.
- Detectar nuevas publicaciones.
- Actualizar base de datos automáticamente.
- Registrar fecha de actualización.
- Mantener historial de archivos fuente.
- Crear logs de ejecución.
- Crear alertas si una carga falla.
- Crear validaciones automáticas antes de actualizar el dashboard.

### Entregable esperado

Un pipeline semi-automático o automático de actualización de datos.

---

## Fase 5 — Capa de IA

**Prioridad:** media.

### Tareas

- Generar resumen ejecutivo del mercado.
- Generar resumen por compañía.
- Generar resumen por ramo.
- Sugerir preguntas para reuniones con clientes.
- Identificar señales técnicas relevantes.
- Crear un módulo de consulta en lenguaje natural.
- Definir reglas para evitar que la IA invente información.
- Limitar la IA a datos públicos y aprobados.

### Entregable esperado

Una capa de inteligencia que convierta datos en insights ejecutivos accionables para brokers.

---

## Fase 6 — Integración corporativa

**Prioridad:** alta antes de uso oficial.

### Tareas

- Revisar el proyecto con IT/Data.
- Definir dónde se alojará la aplicación.
- Revisar permisos de acceso.
- Revisar seguridad.
- Revisar uso de datos públicos.
- Revisar uso de IA.
- Definir responsables de mantenimiento.
- Definir proceso de actualización.
- Definir gobierno de datos.

### Entregable esperado

Una versión aprobada para uso interno corporativo.

---

## Fase 7 — Expansión regional

**Prioridad:** futura.

### Países potenciales

- Colombia.
- México.
- Chile.
- Perú.
- Argentina.
- Costa Rica.
- Panamá.
- Ecuador.
- República Dominicana.

### Tareas

- Identificar reguladores y fuentes por país.
- Revisar formatos disponibles.
- Estandarizar ramos.
- Estandarizar compañías.
- Estandarizar monedas.
- Definir indicadores comparables.
- Crear vista regional.
- Crear vista por país.
- Crear vista comparativa LatAm.

### Entregable esperado

Un hub regional de inteligencia de mercado asegurador para Latinoamérica.

---

## Riesgos y consideraciones

### Calidad de datos

Los datos pueden venir en formatos diferentes, con cambios de estructura entre años o inconsistencias en nombres.

### Actualización

La frecuencia de actualización depende de las fuentes oficiales. El sistema puede revisar diariamente, pero solo podrá actualizarse cuando la fuente publique nueva información.

### Interpretación

Las señales automáticas no deben tomarse como conclusiones finales. Deben servir como punto de partida para análisis broker, revisión técnica y conversación comercial.

### Uso corporativo

Antes de ser usado oficialmente, el proyecto debe revisarse con IT, Data, Compliance y/o Legal.

### IA

La capa de IA debe usarse con cuidado. No debe recibir información confidencial sin aprobación. Debe trabajar inicialmente con datos públicos y estructurados.

---

## Próximos pasos recomendados

1. Validar cifras contra archivos fuente.
2. Mejorar controles de calidad.
3. Refinar visualizaciones.
4. Preparar demo interna.
5. Obtener feedback de brokers.
6. Definir si se escala con apoyo de IT/Data.
7. Evaluar incorporación de IA.
8. Diseñar expansión regional.