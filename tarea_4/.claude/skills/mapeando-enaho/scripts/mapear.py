"""Mapa coroplético de la pobreza monetaria por departamento (ENAHO 2024) y su comparación con la sesión 16.

    uv run .claude/skills/mapeando-enaho/scripts/mapear.py

Une los indicadores con los límites departamentales por CÓDIGO: salidas/indicadores.csv (categoria = ubigeo[:2]) con
FIRST_IDDP del GeoJSON. Nunca por nombre. Los valores son estimaciones PONDERADAS del método oficial del INEI
(hogares, factor07 x mieperho), calculadas por la skill limpiando-enaho: aquí no se calcula ninguna cifra a mano.

Se detiene con error explícito si: falta la base procesada (salidas/personas_2024.parquet), validacion.txt registra una
verificación fallida, no hay exactamente 25 unidades con dato (Lima 15 y Callao 07 separados), o los valores difieren de
la referencia de la sesión 16 más de lo que permite su redondeo (0.05 pp). Guarda mapas/pobreza_departamento_2024.png y
mapas/comparacion_referencia_2024.csv.
"""
import argparse
import sys
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.patheffects as pe
import pandas as pd

matplotlib.use("Agg")   # sin ventanas: solo guarda archivos PNG
from matplotlib import colormaps  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

OFICIAL = "hogares_factor07_x_mieperho"
DEPARTAMENTOS = {f"{i:02d}" for i in range(1, 26)}
TOLERANCIA_REF = 0.05   # la referencia de la sesión 16 está redondeada a 1 decimal: ±0.05 pp
FUENTE = "Fuente: INEI, ENAHO 2024 (módulos 34 y 02). Elaboración propia."
ACENTOS = {"Ancash": "Áncash", "Apurimac": "Apurímac", "Huanuco": "Huánuco", "Junin": "Junín", "San Martin": "San Martín"}


class Falla(Exception):
    """Error explícito que detiene el proceso."""


def nombre_departamento(nombdep: str) -> str:
    """«SAN MARTIN» -> «San Martín», «MADRE DE DIOS» -> «Madre de Dios»."""
    t = " ".join(w.lower() if w in ("DE", "DEL", "LA") and i else w.capitalize() for i, w in enumerate(nombdep.split()))
    return ACENTOS.get(t, t)


def cargar(raiz: Path):
    salidas = raiz / "salidas"
    if not (salidas / "personas_2024.parquet").exists():
        raise Falla("Falta salidas/personas_2024.parquet. Ejecute primero la skill limpiando-enaho "
                    "(uv run .claude/skills/limpiando-enaho/scripts/limpiar.py) y vuelva a mapear.")
    for archivo in ("indicadores.csv", "validacion.txt"):
        if not (salidas / archivo).exists():
            raise Falla(f"Falta salidas/{archivo}. Ejecute primero la skill limpiando-enaho.")
    validacion = (salidas / "validacion.txt").read_text(encoding="utf-8")
    if "[FALLIDA]" in validacion or "TODAS LAS VERIFICACIONES ESENCIALES APROBADAS" not in validacion:
        raise Falla("salidas/validacion.txt registra una verificación fallida: no se mapea con datos no validados.")
    geojson = raiz / "datos" / "peru_departamental_simple.geojson"
    if not geojson.exists():
        raise Falla("Falta datos/peru_departamental_simple.geojson. Ejecute: uv run datos/descargar.py")
    ind = pd.read_csv(salidas / "indicadores.csv", dtype={"categoria": str})
    return ind, gpd.read_file(geojson)


def unir(ind: pd.DataFrame, geo: gpd.GeoDataFrame):
    """Une por código (categoria = ubigeo[:2] con FIRST_IDDP) y exige 25 unidades con dato."""
    geo = geo.assign(FIRST_IDDP=geo["FIRST_IDDP"].astype(str).str.zfill(2))
    d = ind[(ind["dimension"] == "departamento") & (ind["metodo"] == OFICIAL) & (ind["indicador"] == "pobreza monetaria")]
    d = d[["categoria", "valor_pct", "n_muestra"]]
    if set(geo["FIRST_IDDP"]) != DEPARTAMENTOS:
        raise Falla(f"El GeoJSON no trae los 25 códigos 01-25 en FIRST_IDDP: {sorted(set(geo['FIRST_IDDP']))}")
    try:
        m = geo.merge(d, left_on="FIRST_IDDP", right_on="categoria", how="left", validate="1:1", indicator=True)
    except pd.errors.MergeError as e:
        raise Falla(f"La unión por código no es 1:1: {e}") from None
    sin_dato = m.loc[m["valor_pct"].isna(), "FIRST_IDDP"].tolist()
    sobran = sorted(set(d["categoria"]) - set(geo["FIRST_IDDP"]))
    if len(m) != 25 or sin_dato or sobran:
        raise Falla(f"La unión por código debe dar 25 unidades con dato; sin dato: {sin_dato}; indicadores sin geometría: {sobran}.")
    if not {"07", "15"} <= set(m["FIRST_IDDP"]):
        raise Falla("Lima (15) y Callao (07) deben estar separados.")
    m["nombre"] = m["NOMBDEP"].map(nombre_departamento)
    return m


def comparar(m: gpd.GeoDataFrame, ruta_ref: Path, mapas: Path) -> pd.DataFrame:
    """Compara con la referencia de la sesión 16 por código (ccdd = FIRST_IDDP)."""
    ref = pd.read_csv(ruta_ref, dtype={"ccdd": str})
    c = m[["FIRST_IDDP", "nombre", "valor_pct"]].merge(ref[["ccdd", "pobreza_pct"]], left_on="FIRST_IDDP", right_on="ccdd",
                                                       how="outer", validate="1:1", indicator=True)
    if (c["_merge"] != "both").any():
        raise Falla("La referencia de la sesión 16 y el mapa no tienen los mismos códigos de departamento.")
    c = c.rename(columns={"FIRST_IDDP": "codigo", "valor_pct": "calculado_pct", "pobreza_pct": "referencia_sesion16_pct"})
    c["diferencia_pp"] = c["calculado_pct"] - c["referencia_sesion16_pct"]
    c["coincide"] = c["diferencia_pp"].abs() <= TOLERANCIA_REF + 1e-9
    c = c[["codigo", "nombre", "calculado_pct", "referencia_sesion16_pct", "diferencia_pp", "coincide"]].sort_values("codigo")
    mapas.mkdir(exist_ok=True)
    c.to_csv(mapas / "comparacion_referencia_2024.csv", index=False, float_format="%.4f")
    return c


def dibujar(m: gpd.GeoDataFrame, nac: float, raiz: Path) -> Path:
    vmax = float(-(-m["valor_pct"].max() // 5) * 5)   # techo del máximo, de 5 en 5: la escala parte de 0
    cmap, norm = colormaps["OrRd"], Normalize(vmin=0, vmax=vmax)
    alto, bajo = m.loc[m["valor_pct"].idxmax()], m.loc[m["valor_pct"].idxmin()]
    sobre = int((m["valor_pct"] > nac).sum())
    titulo = (f"La pobreza monetaria va de {bajo['valor_pct']:.1f} % en {bajo['nombre']} a {alto['valor_pct']:.1f} % en "
              f"{alto['nombre']}; {sobre} de 25 departamentos superan el promedio nacional ({nac:.1f} %)")
    fig = Figure(figsize=(9, 10.6))
    ax = fig.add_axes([0.04, 0.12, 0.70, 0.74])
    cax = fig.add_axes([0.80, 0.25, 0.03, 0.5])
    fig.text(0.04, 0.975, "\n".join(textwrap.wrap(titulo, 78)), fontsize=12.5, fontweight="bold", va="top")
    fig.text(0.04, 0.905, "Pobreza monetaria por departamento, % de personas · Perú, 2024 · Método oficial del INEI\n"
             "(hogares, factor07 × mieperho)", fontsize=9, color="#444444", va="top")
    m.plot(column="valor_pct", cmap=cmap, norm=norm, edgecolor="white", linewidth=0.6, ax=ax)
    ax.set_axis_off()
    ax.set_aspect(1)
    for _, f in m.iterrows():   # el valor de cada departamento, legible sobre claro u oscuro
        p = f.geometry.representative_point()
        oscuro = norm(f["valor_pct"]) > 0.55
        xy, offset = (p.x, p.y), None
        if f["FIRST_IDDP"] == "07":   # Callao es muy pequeño: su etiqueta va al mar, con una línea
            offset = (-38, -6)
        t = ax.annotate(f"{f['valor_pct']:.1f}", xy, xytext=offset, textcoords="offset points" if offset else "data",
                        fontsize=7.5, ha="center", va="center", color="white" if oscuro and not offset else "#222222",
                        arrowprops={"arrowstyle": "-", "color": "#555555", "lw": 0.6} if offset else None, zorder=6)
        if not offset:
            t.set_path_effects([pe.withStroke(linewidth=1.6, foreground="#00000055" if oscuro else "#ffffffaa")])
    barra = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    barra.set_label("% de personas en pobreza monetaria", fontsize=9)
    barra.set_ticks(range(0, int(vmax) + 1, 5))
    fig.text(0.04, 0.075, "\n".join(textwrap.wrap(
        "Estimaciones ponderadas. Unión por código: ubigeo[:2] = FIRST_IDDP (25 unidades; Lima 15 y Callao 07 por "
        "separado). La escala parte de 0. Las diferencias son descriptivas y no establecen causas.", 110)),
        fontsize=8, color="#666666", va="top")
    fig.text(0.04, 0.025, FUENTE, fontsize=8, color="#666666")
    destino = raiz / "mapas"
    destino.mkdir(exist_ok=True)
    ruta = destino / "pobreza_departamento_2024.png"
    fig.savefig(ruta, dpi=200)
    return ruta


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):   # acentos correctos también en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    skill = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", type=Path, default=skill.parents[2], help="carpeta del proyecto (tarea_4)")
    ap.add_argument("--referencia", type=Path, default=skill / "referencias" / "pobreza_departamento_2024_sesion16.csv")
    a = ap.parse_args()
    raiz = a.raiz.resolve()
    try:
        ind, geo = cargar(raiz)
        m = unir(ind, geo)
        nac = float(ind[(ind["dimension"] == "nacional") & (ind["metodo"] == OFICIAL) &
                        (ind["indicador"] == "pobreza monetaria")]["valor_pct"].iloc[0])
        c = comparar(m, a.referencia, raiz / "mapas")
        print(f"Unión por código: {len(m)} unidades con dato (Lima 15 y Callao 07 separados).")
        print("Comparación con la referencia de la sesión 16 (por departamento):")
        print(c.assign(calculado_pct=c["calculado_pct"].round(2), diferencia_pp=c["diferencia_pp"].round(3)).to_string(index=False))
        malos = c[~c["coincide"]]
        if not malos.empty:
            raise Falla(f"{len(malos)} departamento(s) difieren de la referencia más de {TOLERANCIA_REF} pp: "
                        f"{malos['nombre'].tolist()}. No se guardó el mapa; revise mapas/comparacion_referencia_2024.csv.")
        print(f"Los 25 coinciden con la referencia (diferencia máxima {c['diferencia_pp'].abs().max():.3f} pp, "
              f"tolerancia {TOLERANCIA_REF} pp por el redondeo de la referencia).")
        print(f"OK {dibujar(m, nac, raiz).relative_to(raiz).as_posix()}")
    except Falla as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
