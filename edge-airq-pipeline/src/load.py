"""
load.py  -  ETAPA 4: CARGA (SERVING LAYER)
------------------------------------------
Carga las tablas del warehouse en una base de datos SQLite consultable con SQL.
En un sistema real esto seria Redshift / BigQuery / Snowflake; SQLite es el
equivalente local sin instalar nada (viene con Python). Que las tablas queden
consultables por SQL es lo que las hace utiles para analistas y dashboards.

Ademas ejecuta un par de consultas SQL de ejemplo para demostrar que la capa
de servicio funciona (esto es literalmente lo que valida un data engineer).
"""

import sqlite3

import pandas as pd

from config import DATA_WAREHOUSE, OUTPUT


DB_PATH = OUTPUT / "airquality.db"


def run() -> dict:
    print("\n[4/5] CARGA (SQLite serving layer)  --------------------------")

    conn = sqlite3.connect(DB_PATH)
    tables = ["hourly_by_station", "daily_summary",
              "station_ranking", "latest_status"]
    for t in tables:
        df = pd.read_parquet(DATA_WAREHOUSE / f"{t}.parquet")
        # timestamps a texto para que SQLite los guarde limpios
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str)
            if df[col].dtype == "object":
                df[col] = df[col].astype(str)
        df.to_sql(t, conn, if_exists="replace", index=False)
        print(f"      Cargada tabla '{t}' ({len(df)} filas)")

    # --- Consultas SQL de ejemplo (demuestran la serving layer) ---
    print("\n      Consulta SQL de ejemplo: TOP 3 estaciones mas contaminadas")
    q = """
        SELECT rank, station_name, pm25_avg, level
        FROM station_ranking
        ORDER BY rank
        LIMIT 3;
    """
    top3 = pd.read_sql(q, conn)
    for _, r in top3.iterrows():
        print(f"        #{r['rank']}  {r['station_name']:<10} "
              f"PM2.5={r['pm25_avg']:>5} ug/m3  ({r['level']})")

    conn.close()
    print(f"\n      Base de datos consultable -> output/airquality.db")
    return {"db": str(DB_PATH), "tables": len(tables)}


if __name__ == "__main__":
    run()
