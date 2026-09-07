"""
query_demo.py
-------------
Consultas SQL de ejemplo sobre la serving layer (SQLite). Utcil para
ensenar EN VIVO en la reunion que los datos quedan consultables con SQL,
que es el objetivo final de un pipeline de datos.

Uso:  python src/query_demo.py
"""

import sqlite3
import pandas as pd
from config import OUTPUT

DB = OUTPUT / "airquality.db"

QUERIES = {
    "Ranking de estaciones por PM2.5 medio": """
        SELECT rank, station_name, pm25_avg, level
        FROM station_ranking
        ORDER BY rank;
    """,
    "Media diaria de PM2.5 por estacion": """
        SELECT station_name, date, ROUND(mean,1) AS pm25_medio
        FROM daily_summary
        WHERE pollutant = 'pm2_5'
        ORDER BY station_name, date;
    """,
    "Hora punta: top 5 lecturas horarias de PM2.5 mas altas": """
        SELECT station_name, hour, avg_value AS pm25
        FROM hourly_by_station
        WHERE pollutant = 'pm2_5'
        ORDER BY avg_value DESC
        LIMIT 5;
    """,
    "Estado actual por estacion": """
        SELECT station_name, pm25_last, level
        FROM latest_status
        ORDER BY pm25_last DESC;
    """,
}


def main():
    conn = sqlite3.connect(DB)
    for title, sql in QUERIES.items():
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
        print(pd.read_sql(sql, conn).to_string(index=False))
    conn.close()
    print()


if __name__ == "__main__":
    main()
