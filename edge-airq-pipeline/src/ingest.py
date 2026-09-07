"""
ingest.py  -  ETAPA 1: INGESTA
------------------------------
Descarga la telemetria ambiental de cada estacion desde la API publica
Open-Meteo. Guarda el JSON crudo tal cual llega (raw layer): en data
engineering NUNCA se transforma antes de guardar el crudo, porque si algo
falla mas adelante quieres poder reprocesar desde el origen intacto.

Incluye un FALLBACK a datos sinteticos si no hay internet, igual que un
gateway edge sigue funcionando offline. Asi la demo nunca se cae.
"""

import json
import math
import random
from datetime import datetime, timedelta

import requests

from config import (API_URL, DATA_RAW, PAST_DAYS, POLLUTANTS, STATIONS)


def _fetch_station(station: dict) -> dict:
    """Pide a la API los datos horarios de una estacion. Devuelve el JSON crudo."""
    params = {
        "latitude": station["lat"],
        "longitude": station["lon"],
        "hourly": ",".join(POLLUTANTS),
        "past_days": PAST_DAYS,
        "forecast_days": 0,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _synthetic_station(station: dict) -> dict:
    """
    Genera telemetria sintetica realista si la API no esta disponible.
    Simula un ciclo diario (mas contaminacion en horas punta) + ruido.
    Este es el 'modo offline' del edge node.
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    n_hours = PAST_DAYS * 24
    times = [(now - timedelta(hours=n_hours - i)).strftime("%Y-%m-%dT%H:%M")
             for i in range(n_hours)]

    # base por ciudad para que cada estacion sea distinta
    base = 15 + (hash(station["id"]) % 20)

    def daily_curve(hour):
        # dos picos: manana (8h) y tarde (19h)
        return 1 + 0.6 * (math.exp(-((hour - 8) ** 2) / 8) +
                          math.exp(-((hour - 19) ** 2) / 8))

    hourly = {"time": times}
    for pol in POLLUTANTS:
        scale = {"pm10": 1.4, "pm2_5": 1.0, "carbon_monoxide": 20,
                 "nitrogen_dioxide": 1.8, "ozone": 2.2}.get(pol, 1.0)
        vals = []
        for t in times:
            h = int(t[11:13])
            v = base * scale * daily_curve(h) * random.uniform(0.7, 1.3)
            # inyectamos algunos fallos a proposito para que data quality tenga
            # algo que detectar en la demo (5% nulos, algun outlier)
            r = random.random()
            if r < 0.03:
                v = None                     # sensor caido -> valor nulo
            elif r < 0.05:
                v = base * scale * 12        # pico anomalo -> outlier detectable
            vals.append(round(v, 1) if v is not None else None)
        hourly[pol] = vals

    return {"latitude": station["lat"], "longitude": station["lon"],
            "hourly": hourly, "_synthetic": True}


def run() -> dict:
    """Ingesta todas las estaciones. Devuelve un resumen para el orquestador."""
    print("\n[1/6] INGESTA  -----------------------------------------------")
    summary = {"stations": 0, "source": "api", "records": 0}

    for st in STATIONS:
        try:
            raw = _fetch_station(st)
            src = "api"
        except Exception as e:
            # Fallback: modo offline (como un gateway edge sin conexion)
            print(f"      ! {st['id']}: API no disponible ({type(e).__name__}), "
                  f"usando datos sinteticos")
            raw = _synthetic_station(st)
            src = "synthetic"

        # anotamos metadatos de ingesta (linaje): de donde y cuando vino el dato
        raw["_station_id"] = st["id"]
        raw["_station_name"] = st["name"]
        raw["_ingested_at"] = datetime.utcnow().isoformat()
        raw["_source"] = src

        out = DATA_RAW / f"{st['id']}.json"
        out.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        n = len(raw["hourly"]["time"])
        summary["stations"] += 1
        summary["records"] += n * len(POLLUTANTS)
        if src == "synthetic":
            summary["source"] = "synthetic"
        print(f"      OK {st['id']} ({st['name']:<10}) -> {n} horas x "
              f"{len(POLLUTANTS)} sensores  [{src}]")

    print(f"      Total: {summary['stations']} estaciones, "
          f"{summary['records']} lecturas crudas guardadas en data/raw/")
    return summary


if __name__ == "__main__":
    run()
