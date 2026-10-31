"""Gráfico de barras de la pobreza ponderada (facpob07) por área, sexo o edad."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("por", choices=["area", "sexo", "edad"])
p.add_argument("--anio", type=int, default=2024)
a = p.parse_args()
NOMBRE = {"area": "área", "sexo": "sexo", "edad": "grupo de edad"}

df = pd.read_parquet(f"salidas/personas_{a.anio}.parquet")
if a.por == "area":
    df["grupo"] = df.urbano.map({True: "Urbano", False: "Rural"})
elif a.por == "sexo":
    df["grupo"] = df.mujer.map({True: "Mujeres", False: "Hombres"})
else:
    df["grupo"] = pd.cut(df.edad, [-1, 13, 17, 29, 44, 59, 200],
                         labels=["0-13", "14-17", "18-29", "30-44", "45-59", "60+"]).astype(str)

t = (df.assign(w=df.pobre * df.facpob07).groupby("grupo")[["w", "facpob07"]].sum()
     .pipe(lambda g: (100 * g.w / g.facpob07).astype(float)).sort_values())

fig, ax = plt.subplots(figsize=(7, 0.6 * len(t) + 1.5))
bars = ax.barh(t.index, t.values, color="#2b6cb0")
ax.bar_label(bars, labels=[f"{v:.1f} %" for v in t.values], padding=3)
ax.set_xlim(0, t.max() * 1.15)
ax.set_xlabel("% de personas en pobreza monetaria")
ax.set_title(f"Pobreza monetaria por {NOMBRE[a.por]}, Perú {a.anio}", loc="left")
ax.spines[["top", "right"]].set_visible(False)
fig.text(0.01, 0.01, f"Fuente: INEI, ENAHO {a.anio}. Ponderado con facpob07.", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.04, 1, 1))
Path("figuras").mkdir(exist_ok=True)
out = f"figuras/pobreza_{a.por}_{a.anio}.png"
fig.savefig(out, dpi=200)
print(t.astype(float).round(1).to_string())
print(out)
