# Installation Guide — Colombia Insurance Market Intelligence

## Objetivo

Esta guía explica cómo replicar y ejecutar el MVP en otra computadora.

El proyecto fue construido en Python, usando Streamlit para el dashboard, DuckDB como base local y pandas para procesamiento de datos.

---

## 1. Requisitos previos

Antes de ejecutar el proyecto, la computadora debe tener instalado:

- Python 3.11 o superior.
- Acceso a la carpeta completa del proyecto.
- Archivos de datos públicos de Fasecolda.
- Permisos para instalar librerías de Python.

---

## 2. Estructura esperada del proyecto

La carpeta debe mantener esta estructura:

```text
colombia_insurance_market_dashboard/
│
├── app/
│   └── streamlit_app.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── database/
│
├── docs/
├── notebooks/
├── outputs/
├── src/
├── requirements.txt
└── README.md