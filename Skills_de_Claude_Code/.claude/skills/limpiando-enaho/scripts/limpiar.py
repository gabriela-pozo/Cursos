"""Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO y arma una base de personas."""
import argparse
import zipfile
from pathlib import Path

import pandas as pd

CODIGOS = {2024: 966}
LLAVES = ["conglome", "vivienda", "hogar"]
POBREZA_INEI = {2024: 27.6}

p = argparse.ArgumentParser()
p.add_argument("--anio", type=int, default=2024)
p.add_argument("--datos", default="datos")
p.add_argument("--salidas", default="salidas")
a = p.parse_args()
cod = CODIGOS[a.anio]
datos, salidas = Path(a.datos), Path(a.salidas)
salidas.mkdir(exist_ok=True)


def leer(modulo, patron, cols):
    with zipfile.ZipFile(datos / f"{cod}-Modulo{modulo}.zip") as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(patron))
        with z.open(nombre) as f:
            df = pd.read_stata(f, convert_categoricals=False)
    df.columns = df.columns.str.lower()
    df = df[[c for c in cols if c in df.columns]]
    for k in LLAVES + ["codperso", "ubigeo"]:
        if k in df.columns:
            df[k] = df[k].astype(str).str.strip()
    return df


hog = leer("34", f"sumaria-{a.anio}.dta",
           LLAVES + ["ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07"])
per = leer("02", f"enaho01-{a.anio}-200.dta",
           LLAVES + ["codperso", "p204", "p205", "p206", "p207", "p208a", "facpob07"])
n_per_bruto = len(per)

assert not hog.duplicated(LLAVES).any(), "Llaves de hogar duplicadas"
assert not per.duplicated(LLAVES + ["codperso"]).any(), "Llaves de persona duplicadas"

res = ((per.p204 == 1) & (per.p205 == 2)) | ((per.p204 == 2) & (per.p206 == 1))
per = per[res]
n_res = len(per)

df = per.merge(hog, on=LLAVES, how="left", validate="m:1", indicator=True)
assert len(df) == n_res, "La unión cambió el número de filas"
assert (df._merge == "both").all(), "Personas sin hogar en la sumaria"
df = df.drop(columns="_merge")

df["departamento"] = df.ubigeo.str.zfill(6).str[:2]
df["urbano"] = df.estrato <= 5
df["pobre"] = df.pobreza <= 2
df["pobre_extremo"] = df.pobreza == 1
df["mujer"] = df.p207 == 2
df["edad"] = df.p208a
df["anio"] = a.anio


def pct(d, col="pobre"):
    return 100 * (d[col] * d.facpob07).sum() / d.facpob07.sum()


pob_hog = 100 * (hog.pobreza <= 2).mul(hog.factor07 * hog.mieperho).sum() / (hog.factor07 * hog.mieperho).sum()
pob = pct(df)
dif = abs(pob - POBREZA_INEI[a.anio])
assert dif <= 0.1, f"Pobreza {pob:.2f} % difiere del INEI ({POBREZA_INEI[a.anio]} %)"
assert df.departamento.nunique() == 25

df.to_parquet(salidas / f"personas_{a.anio}.parquet", index=False)
lineas = [
    f"ENAHO {a.anio} - validación",
    f"Hogares en la sumaria: {len(hog):,}",
    f"Filas del módulo 02: {n_per_bruto:,}",
    f"Residentes habituales: {n_res:,}",
    f"Filas tras la unión m:1: {len(df):,} (sin pérdidas ni duplicados)",
    f"Departamentos: {df.departamento.nunique()}",
    f"Pobreza monetaria (personas, facpob07): {pob:.2f} %",
    f"Pobreza monetaria (sumaria, factor07 x mieperho): {pob_hog:.2f} %",
    f"Pobreza oficial INEI: {POBREZA_INEI[a.anio]} % -> diferencia {dif:.2f} pp: OK",
    f"Pobreza extrema: {pct(df, 'pobre_extremo'):.2f} %",
    f"Urbano: {pct(df[df.urbano]):.2f} % | Rural: {pct(df[~df.urbano]):.2f} %",
    f"Lima Metropolitana (dominio 8): {pct(df[df.dominio == 8]):.2f} %",
]
(salidas / "validacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print("\n".join(lineas))
