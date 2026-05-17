# Colombia Insurance Market Intelligence — MVP

## 1. Contexto

Actualmente, la información del mercado asegurador colombiano está disponible en fuentes públicas como Fasecolda y la Superintendencia Financiera. Sin embargo, esta información suele estar dispersa en múltiples archivos, formatos y periodos, lo que hace que el análisis sea manual, lento y poco escalable.

Para un broker, esta información es especialmente valiosa porque permite entender la evolución de compañías, ramos, primas, siniestros, siniestralidad y participación de mercado antes de reuniones comerciales o técnicas.

## 2. Problema identificado

Los brokers necesitan llegar mejor preparados a sus conversaciones con clientes, mercados y equipos internos. Sin embargo, hoy gran parte del análisis de mercado requiere descargar archivos, limpiar datos, cruzar información y construir gráficos manualmente.

Esto genera tres problemas:

- Pérdida de tiempo.
- Dificultad para comparar compañías y ramos de forma consistente.
- Menor capacidad para detectar señales comerciales o técnicas de forma rápida.

## 3. Solución propuesta

Desarrollar una plataforma interna de inteligencia de mercado asegurador que consolide información pública, la estructure en una base de datos y permita visualizar indicadores clave de forma interactiva.

La primera versión se construyó como un MVP enfocado en Colombia, utilizando información pública de Fasecolda para el periodo 2015-2024.

## 4. Qué permite hacer el MVP

La versión actual permite:

- Visualizar primas, siniestros y siniestralidad.
- Filtrar por año, compañía, ramo y ciudad.
- Analizar la evolución histórica del mercado.
- Explorar el desempeño de una compañía específica.
- Analizar un ramo específico.
- Identificar señales técnicas iniciales.
- Descargar información filtrada para análisis adicional.

## 5. Valor para brokers

Esta herramienta puede ayudar a los brokers a:

- Preparar reuniones con mayor profundidad.
- Detectar tendencias técnicas y comerciales.
- Identificar compañías con crecimiento relevante.
- Identificar ramos con deterioro de siniestralidad.
- Comparar desempeño entre aseguradoras.
- Generar conversaciones más estratégicas con clientes y mercados.
- Reducir tiempo de análisis manual.

## 6. Ejemplo de uso

Antes de una reunión con una aseguradora, un broker podría usar la herramienta para revisar:

- Evolución de primas de la compañía.
- Evolución de siniestros.
- Siniestralidad por año.
- Principales ramos de la compañía.
- Participación relativa frente al mercado.
- Ramos donde podría haber oportunidades de conversación técnica o comercial.

## 7. Estado actual

El MVP ya cuenta con:

- Base de datos local en DuckDB.
- Dashboard interactivo en Streamlit.
- Datos públicos consolidados de Fasecolda.
- Filtros dinámicos.
- Visualizaciones de mercado, compañía y ramo.
- Pestaña de señales técnicas.
- Tabla descargable.

## 8. Roadmap sugerido

### Fase 1 — MVP Colombia

Estado: completado en versión inicial.

Incluye consolidación de información pública de Fasecolda, dashboard interactivo y análisis básico de primas, siniestros y siniestralidad.

### Fase 2 — Validación y robustecimiento

- Validar cifras contra archivos fuente.
- Mejorar controles de calidad.
- Documentar metodología.
- Refinar nombres de compañías y ramos.
- Revisar tratamiento de cifras acumuladas, mensuales y anuales.

### Fase 3 — Automatización

- Automatizar descarga de archivos.
- Detectar nuevas publicaciones.
- Actualizar la base de datos automáticamente.
- Registrar fecha de actualización y validaciones.

### Fase 4 — Capa de IA

- Generar insights ejecutivos automáticos.
- Crear resúmenes por compañía.
- Crear resúmenes por ramo.
- Sugerir preguntas para reuniones comerciales o técnicas.
- Permitir consultas en lenguaje natural sobre los datos.

### Fase 5 — Expansión regional

- Extender el modelo a otros países de Latinoamérica.
- Estandarizar fuentes regulatorias.
- Crear una vista regional comparativa.
- Incorporar indicadores adicionales según disponibilidad por país.

## 9. Consideraciones importantes

Este MVP utiliza únicamente información pública y fue desarrollado como una prueba funcional inicial.

Antes de convertirlo en una herramienta oficial, sería recomendable involucrar a equipos de IT, Data, Compliance y/o Legal para revisar temas de infraestructura, seguridad, actualización de datos, uso de IA y gobierno de información.

## 10. Mensaje ejecutivo

Este proyecto busca convertir información pública dispersa en inteligencia accionable para brokers.

La visión es construir un hub regional de inteligencia de mercado asegurador que permita a los equipos comerciales y técnicos llegar mejor preparados a cada conversación, identificar oportunidades más rápido y elevar la calidad del asesoramiento frente a clientes y mercados.