"""
config.py
---------
Configuracion central del pipeline. Tener todo aqui (paths, estaciones,
parametros) en vez de esparcido por el codigo es una practica basica de
data engineering: cambiar una estacion o un umbral no obliga a tocar la logica.
"""

from pathlib import Path

# --- Rutas del proyecto (todo relativo a la raiz del repo) ---
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"            # datos crudos tal cual llegan de la API
DATA_PROCESSED = ROOT / "data" / "processed"  # datos limpios y validados
DATA_WAREHOUSE = ROOT / "data" / "warehouse"  # tablas analiticas finales (Parquet)
OUTPUT = ROOT / "output"                      # graficos y reportes

for _p in (DATA_RAW, DATA_PROCESSED, DATA_WAREHOUSE, OUTPUT):
    _p.mkdir(parents=True, exist_ok=True)

# --- API publica: Open-Meteo Air Quality (gratis, sin API key) ---
API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Contaminantes que pedimos. Cada uno es un "sensor" en la analogia IoT.
POLLUTANTS = ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "ozone"]

# "Estaciones" = nodos edge distribuidos geograficamente.
# Cada estacion es como un gateway con sus sensores ambientales.
STATIONS = [
    {"id": "BCN-01", "name": "Barcelona",  "lat": 41.3874, "lon": 2.1686},
    {"id": "MAD-01", "name": "Madrid",     "lat": 40.4168, "lon": -3.7038},
    {"id": "VLC-01", "name": "Valencia",   "lat": 39.4699, "lon": -0.3763},
    {"id": "SVQ-01", "name": "Sevilla",    "lat": 37.3891, "lon": -5.9845},
    {"id": "BIO-01", "name": "Bilbao",     "lat": 43.2630, "lon": -2.9350},
]

# Cuantos dias historicos pedimos a la API.
PAST_DAYS = 3

# --- Umbrales de calidad de datos (data quality) ---
# Rangos plausibles en ug/m3 basados en maximos historicos realistas.
# Fuera de esto = medida sospechosa (sensor defectuoso o error de lectura).
VALID_RANGES = {
    "pm10":             (0, 600),
    "pm2_5":            (0, 250),
    "carbon_monoxide":  (0, 15000),
    "nitrogen_dioxide": (0, 400),
    "ozone":            (0, 500),
}

# Umbrales de salud OMS/UE (aprox) para clasificar niveles de PM2.5 (ug/m3).
PM25_LEVELS = [
    (0,   10,  "Bueno"),
    (10,  25,  "Moderado"),
    (25,  50,  "Insalubre (sensibles)"),
    (50,  75,  "Insalubre"),
    (75,  999, "Muy insalubre"),
]
