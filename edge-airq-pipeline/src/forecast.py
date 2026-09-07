"""
forecast.py  -  ETAPA 4: FORECASTING
-------------------------------------
Entrena un modelo de regresion simple para predecir el PM2.5 de la hora
siguiente a partir de las lecturas de la hora actual. Es el primer paso hacia
analitica predictiva sobre el warehouse: en vez de solo describir lo que paso
(dashboard), el pipeline empieza a anticipar lo que va a pasar.

Features (hora t):   pm10, pm2_5, ozono, NO2, CO
Target  (hora t+1):  pm2_5

Se entrena un modelo por estacion (cada una tiene su propia dinamica), con un
split cronologico train/test: las ultimas horas se reservan para evaluar y
nunca se usan para entrenar, para no filtrar informacion del futuro.
"""

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from config import DATA_PROCESSED, DATA_WAREHOUSE

FEATURES = ["pm10", "pm2_5", "ozone", "nitrogen_dioxide", "carbon_monoxide"]
TARGET = "pm2_5"
TEST_HOURS = 12  # ultimas 12h de cada estacion se reservan para evaluar
MIN_ROWS = TEST_HOURS + 10  # minimo de horas para entrenar con garantias


def _wide_by_station(df: pd.DataFrame) -> pd.DataFrame:
    """Pivota lecturas largas -> anchas (una fila por hora, una columna por sensor)."""
    return (df.pivot_table(index=["station_id", "station_name", "hour"],
                           columns="pollutant", values="value")
              .reset_index().sort_values(["station_id", "hour"]))


def _forecast_station(g: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Entrena y evalua un modelo para una estacion. Devuelve predicciones + metricas."""
    g = g.dropna(subset=FEATURES).sort_values("hour").reset_index(drop=True)
    g["pm25_next"] = g[TARGET].shift(-1)     # objetivo: PM2.5 de la hora siguiente
    g["target_hour"] = g["hour"].shift(-1)   # a que hora corresponde ese objetivo
    g = g.dropna(subset=["pm25_next"])

    split = len(g) - TEST_HOURS
    train, test = g.iloc[:split], g.iloc[split:]

    model = LinearRegression()
    model.fit(train[FEATURES], train["pm25_next"])
    pred_train = model.predict(train[FEATURES])
    pred_test = model.predict(test[FEATURES])

    rows = pd.concat([
        pd.DataFrame({"hour": train["target_hour"], "pm25_actual": train["pm25_next"],
                      "pm25_predicted": pred_train, "split": "train"}),
        pd.DataFrame({"hour": test["target_hour"], "pm25_actual": test["pm25_next"],
                      "pm25_predicted": pred_test, "split": "test"}),
    ])
    rows["station_id"] = g["station_id"].iloc[0]
    rows["station_name"] = g["station_name"].iloc[0]

    metrics = {
        "station_id": g["station_id"].iloc[0],
        "station_name": g["station_name"].iloc[0],
        "mae": round(mean_absolute_error(test["pm25_next"], pred_test), 2),
        "r2": round(r2_score(test["pm25_next"], pred_test), 3),
    }
    return rows, metrics


def run() -> dict:
    print("\n[4/6] FORECASTING  -------------------------------------------")
    df = pd.read_parquet(DATA_PROCESSED / "measurements_clean.parquet")
    df["hour"] = df["timestamp"].dt.floor("h")
    wide = _wide_by_station(df)

    all_rows, all_metrics = [], []
    for sid, g in wide.groupby("station_id"):
        if len(g) < MIN_ROWS:
            print(f"      ! {sid}: pocas horas, se omite del forecasting")
            continue
        rows, metrics = _forecast_station(g)
        all_rows.append(rows)
        all_metrics.append(metrics)

    forecast = pd.concat(all_rows, ignore_index=True)
    forecast["pm25_actual"] = forecast["pm25_actual"].round(1)
    forecast["pm25_predicted"] = forecast["pm25_predicted"].round(1)
    forecast = forecast.sort_values(["station_id", "hour"])
    forecast.to_parquet(DATA_WAREHOUSE / "forecast.parquet", index=False)

    metrics_df = pd.DataFrame(all_metrics).sort_values("mae").reset_index(drop=True)
    metrics_df.to_parquet(DATA_WAREHOUSE / "forecast_metrics.parquet", index=False)

    print(f"      Modelo: Linear Regression  (features: {', '.join(FEATURES)})")
    print(f"      Objetivo: PM2.5 de la hora siguiente, evaluado en las "
          f"ultimas {TEST_HOURS}h de cada estacion")
    for _, m in metrics_df.iterrows():
        print(f"      {m['station_name']:<10} MAE={m['mae']:<6} R2={m['r2']}")
    print(f"      Guardado forecast.parquet ({len(forecast)} filas) y "
          f"forecast_metrics.parquet ({len(metrics_df)} filas)")

    return {"rows": len(forecast), "metrics": metrics_df}


if __name__ == "__main__":
    run()
