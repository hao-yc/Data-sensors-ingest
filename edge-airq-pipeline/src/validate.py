"""
validate.py  -  ETAPA 2: VALIDACION / DATA QUALITY
--------------------------------------------------
Convierte el JSON crudo (formato 'columnas paralelas' de la API) a un
formato tabular largo (una fila = una lectura) y aplica reglas de calidad:

  - Parseo y normalizacion de tipos.
  - Deteccion de nulos (sensor caido).
  - Deteccion de outliers (valor fuera de rango fisico plausible).
  - Deduplicacion (misma estacion+sensor+timestamp repetido).

Genera un reporte de calidad. Data quality es de los temas mas valorados
en entrevistas de data engineering y casi nadie lo trabaja de junior.
"""

import json

import pandas as pd

from config import DATA_PROCESSED, DATA_RAW, POLLUTANTS, VALID_RANGES


def _raw_to_long(raw: dict) -> pd.DataFrame:
    """De {time:[...], pm10:[...], ...} a filas (station, ts, pollutant, value)."""
    h = raw["hourly"]
    rows = []
    for i, ts in enumerate(h["time"]):
        for pol in POLLUTANTS:
            rows.append({
                "station_id": raw["_station_id"],
                "station_name": raw["_station_name"],
                "timestamp": ts,
                "pollutant": pol,
                "value": h.get(pol, [None] * len(h["time"]))[i],
                "source": raw.get("_source", "unknown"),
            })
    return pd.DataFrame(rows)


def run() -> dict:
    """Lee todos los crudos, valida y guarda un dataset limpio en Parquet."""
    print("\n[2/5] VALIDACION / DATA QUALITY  -----------------------------")

    frames = [_raw_to_long(json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(DATA_RAW.glob("*.json"))]
    df = pd.concat(frames, ignore_index=True)

    total_in = len(df)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # --- Regla 1: nulos (sensor caido / gap de datos) ---
    n_nulls = int(df["value"].isna().sum())

    # --- Regla 2: outliers (fuera de rango fisico plausible) ---
    def _in_range(row):
        lo, hi = VALID_RANGES.get(row["pollutant"], (float("-inf"), float("inf")))
        if pd.isna(row["value"]):
            return True  # los nulos se tratan aparte
        return lo <= row["value"] <= hi

    mask_valid_range = df.apply(_in_range, axis=1)
    n_outliers = int((~mask_valid_range).sum())

    # --- Regla 3: duplicados (misma estacion+sensor+timestamp) ---
    dup_mask = df.duplicated(subset=["station_id", "pollutant", "timestamp"],
                             keep="first")
    n_dupes = int(dup_mask.sum())

    # Aplicamos limpieza: quitamos duplicados y outliers, marcamos nulos
    clean = df[~dup_mask & mask_valid_range].copy()
    clean = clean.dropna(subset=["value"])

    total_out = len(clean)
    quality_pct = round(100 * total_out / total_in, 1) if total_in else 0

    # Guardamos el dataset limpio en Parquet (formato columnar estandar en DE:
    # comprime mejor y se lee mucho mas rapido que CSV/JSON)
    out = DATA_PROCESSED / "measurements_clean.parquet"
    clean.to_parquet(out, index=False)

    report = {
        "rows_in": total_in,
        "rows_out": total_out,
        "nulls": n_nulls,
        "outliers": n_outliers,
        "duplicates": n_dupes,
        "quality_pct": quality_pct,
    }

    print(f"      Lecturas de entrada : {total_in}")
    print(f"      Nulos (sensor caido): {n_nulls}")
    print(f"      Outliers eliminados : {n_outliers}")
    print(f"      Duplicados eliminados: {n_dupes}")
    print(f"      Lecturas limpias    : {total_out}  ({quality_pct}% aprovechado)")
    print(f"      Guardado -> data/processed/measurements_clean.parquet")
    return report


if __name__ == "__main__":
    run()
