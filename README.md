# Edge Air-Quality Data Pipeline

Pipeline de datos **end-to-end** que ingiere telemetria ambiental de una red de
"estaciones" (nodos edge distribuidos geograficamente), la valida, la transforma
y la deja consultable y visualizada. Un caso practico de **data engineering**
aplicado a un escenario **IoT / edge**: cada estacion es analoga a un gateway con
sus sensores, y el pipeline cubre todo el ciclo de vida del dato desde que se
genera hasta que es util.

![dashboard](output/dashboard.png)

## Por que este proyecto

Reproduce, a pequena escala, lo que hace un data engineer en un sistema real de
telemetria: **garantizar que los datos de dispositivos distribuidos llegan
integros y se convierten en informacion util**. Los problemas que aparecen aqui
(sensores caidos, valores anomalos, duplicados, agregacion temporal, capa de
servicio) son los mismos que en una plataforma IoT de produccion.

## Arquitectura

```
  API publica          data/raw/        data/processed/     data/warehouse/      output/
 (Open-Meteo AQ)         *.json         *.parquet           *.parquet          dashboard.png
       |                   |                 |                   |               airquality.db
       v                   v                 v                   v                   v
  [1] INGESTA  ->  [2] DATA QUALITY  ->  [3] TRANSFORM  ->  [4] LOAD (SQLite)  ->  [5] VISUALIZE
   descarga +        valida, limpia,      agregaciones       serving layer         dashboard PNG
   raw layer +       deduplica,           por ventana        consultable via SQL   + consultas SQL
   fallback offline  detecta outliers     temporal / ranking
```

Cada etapa **lee de la anterior y escribe para la siguiente** (etapas idempotentes),
igual que las tareas de un DAG de Airflow. Un solo comando ejecuta todo.

## Etapas

| # | Etapa | Que hace | Concepto de data engineering |
|---|-------|----------|------------------------------|
| 1 | **Ingesta** | Descarga telemetria horaria de cada estacion via API REST. Guarda el JSON crudo intacto. Fallback a datos sinteticos si no hay red. | Raw layer, idempotencia, linaje, tolerancia a fallos |
| 2 | **Data quality** | Pasa a formato tabular largo; detecta y elimina nulos, outliers (fuera de rango fisico) y duplicados. Reporta % aprovechado. | Data validation, deduplicacion, calidad de datos |
| 3 | **Transformacion** | Agregaciones por ventana temporal (horaria/diaria), ranking de estaciones, tabla de estado. Guarda en Parquet. | Modelado analitico, formatos columnares |
| 4 | **Carga** | Consolida las tablas en una BD SQLite consultable con SQL. Ejecuta consultas de ejemplo. | Serving layer, warehouse |
| 5 | **Visualizacion** | Genera un dashboard PNG: serie temporal, ranking, resumen diario, estado actual. | Consumo / BI |

## Como ejecutar

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar el pipeline completo (un solo comando)
python src/run_pipeline.py

# 3. (opcional) Consultar la base de datos con SQL en vivo
python src/query_demo.py
```

Salidas en `output/`:
- `dashboard.png` - panel visual con 4 graficos
- `airquality.db` - base de datos SQLite consultable

> **Nota:** si hay conexion, usa datos reales de la API publica de Open-Meteo Air
> Quality (gratis, sin API key). Si no hay red, el pipeline genera datos
> sinteticos realistas automaticamente (modo offline), asi que **siempre corre**.

## Stack

- **Python** (requests, pandas)
- **Parquet** via pyarrow (formato columnar, estandar en data engineering)
- **SQLite** como serving layer consultable por SQL
- **matplotlib** para el dashboard
- Fuente: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)

## Estructura

```
edge-airq-pipeline/
├── src/
│   ├── config.py         # configuracion central (estaciones, umbrales, rutas)
│   ├── ingest.py         # [1] ingesta + fallback offline
│   ├── validate.py       # [2] data quality
│   ├── transform.py      # [3] agregaciones analiticas
│   ├── load.py           # [4] carga en SQLite
│   ├── visualize.py      # [5] dashboard
│   ├── run_pipeline.py   # orquestador (ejecuta 1->5)
│   └── query_demo.py     # consultas SQL de ejemplo
├── data/
│   ├── raw/              # JSON crudo por estacion
│   ├── processed/        # dataset limpio (Parquet)
│   └── warehouse/        # tablas analiticas (Parquet)
├── output/              # dashboard.png + airquality.db
├── requirements.txt
└── README.md
```

## Proximos pasos (roadmap)

- [ ] Carga incremental (solo lecturas nuevas) en vez de recargar todo
