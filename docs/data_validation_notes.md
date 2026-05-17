# Data Validation Notes — Colombia Insurance Market Intelligence

## Objetivo

Este documento resume los primeros hallazgos de validación del dataset utilizado en el MVP de Colombia Insurance Market Intelligence.

La validación busca identificar posibles temas de calidad de datos antes de presentar o escalar el proyecto internamente.

---

## Dataset validado

**Fuente:** Fasecolda  
**Periodo:** 2015-2024  
**Registros procesados:** 1,199,923  
**Compañías únicas:** 60  
**Ramos únicos:** 26  
**Ciudades únicas:** 34  

---

## Resultados principales

### 1. Cobertura temporal

El dataset contiene información desde enero de 2015 hasta diciembre de 2024.

Esto permite analizar tendencias históricas de 10 años en primas, siniestros y siniestralidad.

---

### 2. Tipos de valor

El dataset contiene dos tipos principales de valores:

- Primas
- Siniestros

Estos campos permiten calcular siniestralidad como:

```text
Siniestralidad = Siniestros / Primas