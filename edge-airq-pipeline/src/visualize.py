"""
visualize.py  -  ETAPA 5: VISUALIZACION
---------------------------------------
Genera un dashboard en PNG a partir de las tablas del warehouse. Es la salida
que ensenas en la reunion: un panel con serie temporal, ranking, resumen
diario y estado actual. Un data engineer no suele hacer el dashboard final
(eso es del analista), pero saber cerrar el ciclo hasta 'algo que se ve'
hace que la demo tenga impacto.
"""

import matplotlib
matplotlib.use("Agg")  # backend sin ventana, guarda a fichero
import matplotlib.pyplot as plt
import pandas as pd

from config import DATA_WAREHOUSE, OUTPUT

# paleta sobria
BG = "#0f1a2b"
FG = "#e8edf4"
ACCENT = "#4da3ff"
GRID = "#26374f"
BARS = ["#4da3ff", "#5ecf9e", "#f4b942", "#ff7b6b", "#b28dff"]


def _style(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
    ax.title.set_color(FG)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)


def run() -> dict:
    print("\n[5/5] VISUALIZACION  -----------------------------------------")

    hourly = pd.read_parquet(DATA_WAREHOUSE / "hourly_by_station.parquet")
    hourly["hour"] = pd.to_datetime(hourly["hour"])
    daily = pd.read_parquet(DATA_WAREHOUSE / "daily_summary.parquet")
    ranking = pd.read_parquet(DATA_WAREHOUSE / "station_ranking.parquet")
    latest = pd.read_parquet(DATA_WAREHOUSE / "latest_status.parquet")

    fig = plt.figure(figsize=(15, 9), facecolor=BG)
    fig.suptitle("Edge Air-Quality Pipeline  ·  Dashboard de telemetria ambiental",
                 color=FG, fontsize=17, fontweight="bold", y=0.98)
    fig.text(0.5, 0.94,
             "Ingesta API publica  ->  Data quality  ->  Transformacion  ->  "
             "Warehouse  ->  Visualizacion",
             ha="center", color=ACCENT, fontsize=10)

    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.22,
                          left=0.06, right=0.97, top=0.88, bottom=0.08)

    # --- (1) Serie temporal PM2.5 por estacion ---
    ax1 = fig.add_subplot(gs[0, 0])
    pm = hourly[hourly["pollutant"] == "pm2_5"]
    for i, (sid, g) in enumerate(pm.groupby("station_name")):
        g = g.sort_values("hour")
        ax1.plot(g["hour"], g["avg_value"], label=sid,
                 color=BARS[i % len(BARS)], linewidth=1.6)
    ax1.set_title("PM2.5 - media horaria por estacion", fontsize=11, loc="left")
    ax1.set_ylabel("ug/m3")
    ax1.legend(fontsize=7, facecolor=BG, edgecolor=GRID, labelcolor=FG, ncol=2)
    _style(ax1)
    for lbl in ax1.get_xticklabels():
        lbl.set_rotation(20); lbl.set_ha("right")

    # --- (2) Ranking de estaciones por PM2.5 medio ---
    ax2 = fig.add_subplot(gs[0, 1])
    r = ranking.sort_values("pm25_avg")
    ax2.barh(r["station_name"], r["pm25_avg"],
             color=[BARS[i % len(BARS)] for i in range(len(r))])
    for y, (v, lv) in enumerate(zip(r["pm25_avg"], r["level"])):
        ax2.text(v + 0.3, y, f"{v}", va="center", color=FG, fontsize=8)
    ax2.set_title("Ranking por PM2.5 medio (mas limpio arriba)",
                  fontsize=11, loc="left")
    ax2.set_xlabel("ug/m3")
    _style(ax2)

    # --- (3) Resumen diario apilado: media por contaminante (una estacion) ---
    ax3 = fig.add_subplot(gs[1, 0])
    focus = ranking.iloc[0]["station_name"]  # la mas contaminada
    d = daily[daily["station_name"] == focus].copy()
    # excluimos CO: su escala (miles) aplastaria al resto de contaminantes
    d = d[d["pollutant"] != "carbon_monoxide"]
    pivot = d.pivot_table(index="date", columns="pollutant",
                          values="mean", aggfunc="mean").fillna(0)
    bottom = None
    for i, col in enumerate(pivot.columns):
        ax3.bar(pivot.index.astype(str), pivot[col], bottom=bottom,
                label=col, color=BARS[i % len(BARS)])
        bottom = pivot[col] if bottom is None else bottom + pivot[col]
    ax3.set_title(f"Media diaria por contaminante - {focus} (sin CO)",
                  fontsize=11, loc="left")
    ax3.set_ylabel("ug/m3")
    ax3.legend(fontsize=7, facecolor=BG, edgecolor=GRID, labelcolor=FG)
    _style(ax3)
    for lbl in ax3.get_xticklabels():
        lbl.set_rotation(20); lbl.set_ha("right")

    # --- (4) Estado actual: tarjetas de nivel por estacion ---
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    ax4.set_title("Estado actual (ultima lectura PM2.5)",
                  fontsize=11, loc="left", color=FG)
    level_color = {
        "Bueno": "#5ecf9e", "Moderado": "#f4b942",
        "Insalubre (sensibles)": "#ff9f43", "Insalubre": "#ff7b6b",
        "Muy insalubre": "#c0392b", "Desconocido": "#7f8c8d",
    }
    lt = latest.sort_values("pm25_last", ascending=False).reset_index(drop=True)
    for i, row in lt.iterrows():
        y = 0.85 - i * 0.17
        c = level_color.get(row["level"], "#7f8c8d")
        ax4.add_patch(plt.Rectangle((0.02, y - 0.06), 0.96, 0.13,
                      transform=ax4.transAxes, facecolor=c, alpha=0.22,
                      edgecolor=c, linewidth=1.2))
        ax4.text(0.05, y, f"{row['station_name']}", transform=ax4.transAxes,
                 color=FG, fontsize=11, fontweight="bold", va="center")
        ax4.text(0.55, y, f"{row['pm25_last']:.1f} ug/m3",
                 transform=ax4.transAxes, color=FG, fontsize=10, va="center")
        ax4.text(0.98, y, row["level"], transform=ax4.transAxes,
                 color=c, fontsize=9, va="center", ha="right", fontweight="bold")

    out = OUTPUT / "dashboard.png"
    fig.savefig(out, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"      Dashboard generado -> output/dashboard.png")
    return {"dashboard": str(out)}


if __name__ == "__main__":
    run()
