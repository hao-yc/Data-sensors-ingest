"""
run_pipeline.py  -  ORQUESTADOR
-------------------------------
Ejecuta las 5 etapas del pipeline en orden, como haria Airflow con un DAG
(cada etapa depende de la anterior). Un solo comando corre todo end-to-end:

    python src/run_pipeline.py

Este patron -un orquestador que encadena etapas idempotentes- es el corazon
de cualquier pipeline de datos. Cada etapa lee de la anterior y escribe para
la siguiente, de modo que puedes reejecutar todo o depurar una etapa aislada.
"""

import time
from datetime import datetime

import ingest
import validate
import transform
import load
import visualize


def main():
    t0 = time.time()
    print("=" * 64)
    print("  EDGE AIR-QUALITY DATA PIPELINE")
    print("  Telemetria ambiental edge-to-warehouse (data engineering demo)")
    print(f"  Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 64)

    ing = ingest.run()          # 1. Ingesta
    qual = validate.run()       # 2. Data quality
    transform.run()             # 3. Transformacion
    load.run()                  # 4. Carga (serving layer)
    visualize.run()            # 5. Visualizacion

    dt = time.time() - t0
    print("\n" + "=" * 64)
    print("  PIPELINE COMPLETADO")
    print(f"  Fuente de datos    : {ing['source']}")
    print(f"  Lecturas ingeridas : {ing['records']}")
    print(f"  Calidad de datos   : {qual['quality_pct']}% aprovechado "
          f"({qual['nulls']} nulos, {qual['outliers']} outliers, "
          f"{qual['duplicates']} duplicados)")
    print(f"  Tiempo total       : {dt:.1f}s")
    print("  Salidas: output/dashboard.png  +  output/airquality.db")
    print("=" * 64)


if __name__ == "__main__":
    main()
