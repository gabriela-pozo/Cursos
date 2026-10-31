"""Mapa coroplético de la pobreza por departamento, unido por código (ubigeo[:2] = FIRST_IDDP)."""
import argparse
import urllib.request
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

URL = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
       "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson")
p = argparse.ArgumentParser()
p.add_argument("--anio", type=int, default=2024)
p.add_argument("--geojson", default="datos/peru_departamental_simple.geojson")
a = p.parse_args()

if not Path(a.geojson).exists():
    urllib.request.urlretrieve(URL, a.geojson)

df = pd.read_parquet(f"salidas/personas_{a.anio}.parquet")
t = (df.assign(w=df.pobre * df.facpob07).groupby("departamento")[["w", "facpob07"]].sum()
     .pipe(lambda g: (100 * g.w / g.facpob07).astype(float)).rename("pobreza").reset_index())

geo = gpd.read_file(a.geojson)
geo["departamento"] = geo.FIRST_IDDP.astype(str).str.zfill(2)
m = geo.merge(t, on="departamento", how="left", validate="1:1")
assert len(m) == 25, f"Se esperaban 25 departamentos, hay {len(m)}"
assert m.pobreza.notna().all(), f"Sin dato: {m.loc[m.pobreza.isna(), 'departamento'].tolist()}"

fig, ax = plt.subplots(figsize=(7, 9))
m.plot(column="pobreza", cmap="Reds", vmin=0, vmax=50, edgecolor="white", linewidth=0.5, ax=ax,
       legend=True, legend_kwds={"label": "% de personas en pobreza monetaria", "shrink": 0.6})
ax.set_axis_off()
ax.set_title(f"Pobreza monetaria por departamento, Perú {a.anio}", loc="left")
fig.text(0.02, 0.02, f"Fuente: INEI, ENAHO {a.anio}. Lima (15) y Callao (07) por separado.", fontsize=8, color="gray")
Path("mapas").mkdir(exist_ok=True)
fig.savefig("mapas/pobreza_departamento.png", dpi=200, bbox_inches="tight")
print(m.sort_values("pobreza", ascending=False)[["departamento", "pobreza"]].round(1).to_string(index=False))
print("mapas/pobreza_departamento.png")
