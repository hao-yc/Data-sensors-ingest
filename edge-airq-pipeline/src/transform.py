"""
transform.py  -  ETAPA 3: TRANSFORMACION
----------------------------------------
Convierte las lecturas limpias en tablas analiticas listas para consumo.
Esto es el equivalente a lo que harias con dbt / SQL en un warehouse real:
agregaciones por ventana temporal, ranking, y una tabla de hechos ancha.

Tablas que produce:
  - hourly_by_station : media horaria por estacion y contaminante (serie temporal)
  - daily_summary     : min/media/max diarios por estacion y contaminante
  - station_ranking   : ranking de estaciones por PM2.5 medio (mas sucio -> mas limpio)
  - latest_status     : ultima lectura de PM2.5 por estacion + nivel de salud
"""

import pandas as pd

from config import DATA_PROCESSED, DATA_WAREHOUSE, PM25_LEVELS


def _pm25_level(value: float) -> str:
    for lo, hi, label in PM25_LEVELS:
        if lo <= value < hi:
            return label
    return "Desconocido"


def run() -> dict:
    print("\n[3/6] TRANSFORMACION  ----------------------------------------")
    df = pd.read_parquet(DATA_PROCESSED / "measurements_clean.parquet")
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.floor("h")

    # --- Tabla 1: media horaria (serie temporal por estacion+contaminante) ---
    hourly = (df.groupby(["station_id", "station_name", "pollutant", "hour"],
                         as_index=False)["value"].mean()
                .rename(columns={"value": "avg_value"}))
    hourly["avg_value"] = hourly["avg_value"].round(1)
    hourly.to_parquet(DATA_WAREHOUSE / "hourly_by_station.parquet", index=False)

    # --- Tabla 2: resumen diario (min/media/max) ---
    daily = (df.groupby(["station_id", "station_name", "pollutant", "date"])
               ["value"].agg(["min", "mean", "max"]).round(1).reset_index())
    daily.to_parquet(DATA_WAREHOUSE / "daily_summary.parquet", index=False)

    # --- Tabla 3: ranking de estaciones por PM2.5 medio ---
    pm = df[df["pollutant"] == "pm2_5"]
    ranking = (pm.groupby(["station_id", "station_name"], as_index=False)["value"]
                 .mean().rename(columns={"value": "pm25_avg"}))
    ranking["pm25_avg"] = ranking["pm25_avg"].round(1)
    ranking = ranking.sort_values("pm25_avg", ascending=False).reset_index(drop=True)
    ranking["rank"] = ranking.index + 1
    ranking["level"] = ranking["pm25_avg"].apply(_pm25_level)
    ranking.to_parquet(DATA_WAREHOUSE / "station_ranking.parquet", index=False)

    # --- Tabla 4: ultimo estado por estacion ---
    latest = (pm.sort_values("timestamp")
                .groupby(["station_id", "station_name"], as_index=False).last()
                [["station_id", "station_name", "timestamp", "value"]]
                .rename(columns={"value": "pm25_last"}))
    latest["level"] = latest["pm25_last"].apply(_pm25_level)
    latest.to_parquet(DATA_WAREHOUSE / "latest_status.parquet", index=False)

    print(f"      hourly_by_station : {len(hourly):>4} filas")
    print(f"      daily_summary     : {len(daily):>4} filas")
    print(f"      station_ranking   : {len(ranking):>4} filas")
    print(f"      latest_status     : {len(latest):>4} filas")
    print(f"      Guardado en data/warehouse/ (4 tablas Parquet)")

    return {"tables": 4, "ranking": ranking, "latest": latest}


if __name__ == "__main__":
    run()
