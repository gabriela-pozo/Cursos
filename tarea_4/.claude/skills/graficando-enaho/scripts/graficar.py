"""Gráficos de pobreza monetaria de la ENAHO 2024: por área (urbano/rural), por sexo y por departamento.

    uv run .claude/skills/graficando-enaho/scripts/graficar.py --grafico {area,sexo,departamento,todos}

Lee salidas/indicadores.csv, que genera la skill limpiando-enaho a partir de los microdatos con estimaciones
PONDERADAS. Aquí no se calcula ninguna cifra a mano ni se hace ningún promedio simple: solo se dibuja lo que ya salió
del procesamiento, y los títulos arman sus cifras desde esos mismos datos. Los nombres de departamento vienen de la
columna nombre_categoria de indicadores.csv (diccionario oficial de ubigeo de limpiando-enaho), no de memoria.

  - Área y departamento: método oficial del INEI (hogares, factor07 x mieperho), el de validacion.txt.
  - Sexo: cálculo por personas (facpob07), porque el sexo es un atributo de la persona. Se rotula en el gráfico y
    puede diferir levemente del método oficial.

Si falta la base procesada (salidas/personas_2024.parquet), si faltan los indicadores o si validacion.txt registra una
verificación esencial fallida, termina con un error que dice qué hacer. Guarda los PNG en figuras/.
"""
import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")   # sin ventanas: solo guarda archivos PNG
from matplotlib.figure import Figure  # noqa: E402

OFICIAL = "hogares_factor07_x_mieperho"
PERSONAS = "personas_facpob07"
FUENTE = "Fuente: INEI, ENAHO 2024 (módulos 34 y 02). Elaboración propia."
AZUL, GRIS = "#1f5f8b", "#666666"
DEPARTAMENTOS = [f"{i:02d}" for i in range(1, 26)]


class Falla(Exception):
    """Error explícito que detiene el proceso."""


# ------------------------------------------------------------------------------------------------ insumos
def cargar(raiz: Path) -> pd.DataFrame:
    """Comprueba la base procesada y devuelve los indicadores (con nombre_categoria, del diccionario oficial)."""
    salidas = raiz / "salidas"
    if not (salidas / "personas_2024.parquet").exists():
        raise Falla("Falta salidas/personas_2024.parquet. Ejecute primero la skill limpiando-enaho "
                    "(uv run .claude/skills/limpiando-enaho/scripts/limpiar.py) y vuelva a graficar.")
    for archivo in ("indicadores.csv", "validacion.txt"):
        if not (salidas / archivo).exists():
            raise Falla(f"Falta salidas/{archivo}. Ejecute primero la skill limpiando-enaho.")
    validacion = (salidas / "validacion.txt").read_text(encoding="utf-8")
    if "[FALLIDA]" in validacion or "TODAS LAS VERIFICACIONES ESENCIALES APROBADAS" not in validacion:
        raise Falla("salidas/validacion.txt registra una verificación fallida: no se grafica con datos no validados. "
                    "Revise limpiando-enaho.")
    ind = pd.read_csv(salidas / "indicadores.csv", dtype={"categoria": str})
    if "nombre_categoria" not in ind.columns:
        raise Falla("indicadores.csv no trae nombre_categoria (diccionario oficial de departamentos). "
                    "Vuelva a ejecutar la skill limpiando-enaho.")
    return ind


def filas(ind: pd.DataFrame, dimension: str, metodo: str, categorias=None) -> pd.DataFrame:
    d = ind[(ind["dimension"] == dimension) & (ind["metodo"] == metodo) & (ind["indicador"] == "pobreza monetaria")]
    if categorias is not None:
        d = d[d["categoria"].isin(categorias)]
        if set(d["categoria"]) != set(categorias):
            raise Falla(f"indicadores.csv no trae {sorted(set(categorias) - set(d['categoria']))} "
                        f"({dimension}, {metodo}). Vuelva a ejecutar limpiando-enaho.")
    if d.empty:
        raise Falla(f"indicadores.csv no trae {dimension} con el método {metodo}. Vuelva a ejecutar limpiando-enaho.")
    return d.set_index("categoria")


def nacional(ind: pd.DataFrame) -> float:
    d = ind[(ind["dimension"] == "nacional") & (ind["metodo"] == OFICIAL) & (ind["indicador"] == "pobreza monetaria")]
    return float(d["valor_pct"].iloc[0])


# ------------------------------------------------------------------------------------------------ dibujo
def lienzo(titulo: str, subtitulo: str, nota: str | None, alto: float):
    """Figura con título, subtítulo, nota y fuente. Las medidas van en pulgadas para que nada se pise."""
    fig = Figure(figsize=(10, alto))
    ax = fig.subplots()
    t, sub = textwrap.wrap(titulo, 82), textwrap.wrap(subtitulo, 120)
    n = textwrap.wrap(nota, 125) if nota else []
    y = alto - 0.3                                            # pulgadas medidas desde abajo
    fig.text(0.05, y / alto, "\n".join(t), fontsize=12.5, fontweight="bold", va="top")
    y -= len(t) * 0.26 + 0.12
    fig.text(0.05, y / alto, "\n".join(sub), fontsize=9, color="#444444", va="top")
    y -= len(sub) * 0.17 + 0.35
    if n:
        fig.text(0.05, 0.5 / alto, "\n".join(n), fontsize=8, color=GRIS, va="bottom")
    fig.text(0.05, 0.2 / alto, FUENTE, fontsize=8, color=GRIS, va="bottom")
    abajo = 0.5 + len(n) * 0.16 + 0.95                        # nota + espacio para etiquetas del eje
    fig.subplots_adjust(top=y / alto, bottom=abajo / alto, left=0.12, right=0.95)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    return fig, ax


def guardar(fig, raiz: Path, nombre: str) -> Path:
    destino = raiz / "figuras"
    destino.mkdir(exist_ok=True)
    ruta = destino / nombre
    fig.savefig(ruta, dpi=200)
    return ruta


def barras_verticales(raiz, ind, dimension, metodo, categorias, etiquetas, unidad_n, titulo_fn, subtitulo, nota, nombre):
    d = filas(ind, dimension, metodo, categorias)
    vals = [float(d.loc[c, "valor_pct"]) for c in categorias]
    ns = [int(d.loc[c, "n_muestra"]) for c in categorias]
    fig, ax = lienzo(titulo_fn(dict(zip(categorias, vals))), subtitulo, nota, alto=6.6)
    x = list(range(len(categorias)))
    barras = ax.bar(x, vals, color=AZUL, width=0.5)   # las barras parten de cero
    for b, v in zip(barras, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.015, f"{v:.1f} %", ha="center", fontsize=12, fontweight="bold")
    ax.set_xticks(x, [f"{etiquetas[c]}\n(n = {n:,} {unidad_n})" for c, n in zip(categorias, ns)])
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_ylabel("% de personas en pobreza monetaria")
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    return guardar(fig, raiz, nombre), dict(zip(categorias, vals))


def grafico_area(raiz, ind):
    nac = nacional(ind)
    sub = f"Pobreza monetaria, % de personas · Perú, 2024 · Método oficial del INEI (hogares, factor07 × mieperho) · Nacional: {nac:.1f} %"

    def titulo(v):
        return (f"La pobreza monetaria en el área rural ({v['Rural']:.1f} %) fue {v['Rural'] - v['Urbano']:.1f} puntos "
                f"porcentuales mayor que en la urbana ({v['Urbano']:.1f} %): {v['Rural'] / v['Urbano']:.1f} veces")
    return barras_verticales(raiz, ind, "area", OFICIAL, ["Urbano", "Rural"], {"Urbano": "Urbano", "Rural": "Rural"},
                             "hogares", titulo, sub,
                             "Estimaciones ponderadas. Área urbana: estrato ≤ 5; rural: estrato > 5. n = hogares de la muestra. "
                             "La comparación es descriptiva y no establece causas.", "enaho2024_pobreza_area.png")


def grafico_sexo(raiz, ind):
    sub = ("Pobreza monetaria, % de personas · Perú, 2024 · ESTIMACIÓN POR PERSONAS (facpob07, residentes habituales): "
           "puede diferir levemente del método oficial")

    def titulo(v):
        mayor, menor = ("Mujer", "Hombre") if v["Mujer"] >= v["Hombre"] else ("Hombre", "Mujer")
        return (f"La pobreza monetaria fue de {v['Mujer']:.1f} % entre las mujeres y {v['Hombre']:.1f} % entre los hombres: "
                f"una diferencia de {abs(v['Mujer'] - v['Hombre']):.1f} puntos porcentuales")
    return barras_verticales(raiz, ind, "sexo", PERSONAS, ["Mujer", "Hombre"], {"Mujer": "Mujeres", "Hombre": "Hombres"},
                             "personas", titulo, sub,
                             "Estimaciones ponderadas con facpob07 sobre residentes habituales; el sexo es un atributo de la persona, "
                             "por eso no se usa el método de hogares. Sin intervalos de confianza: la diferencia es descriptiva.",
                             "enaho2024_pobreza_sexo.png")


def grafico_departamento(raiz, ind):
    d = filas(ind, "departamento", OFICIAL, DEPARTAMENTOS)
    if len(d) != 25:
        raise Falla(f"Se esperaban 25 departamentos y hay {len(d)}.")
    # El nombre viene del diccionario oficial de limpiando-enaho (columna nombre_categoria), nunca de memoria
    if d["nombre_categoria"].isna().any() or d["nombre_categoria"].duplicated().any():
        raise Falla("indicadores.csv trae nombres de departamento vacíos o repetidos. Vuelva a ejecutar limpiando-enaho.")
    d = d.assign(nombre=d["nombre_categoria"]).sort_values("valor_pct", ascending=True)
    nac = nacional(ind)
    alto, bajo = d.iloc[-1], d.iloc[0]
    sobre = int((d["valor_pct"] > nac).sum())
    titulo = (f"{alto['nombre']} ({alto['valor_pct']:.1f} %) tuvo la mayor pobreza monetaria y {bajo['nombre']} "
              f"({bajo['valor_pct']:.1f} %) la menor: {alto['valor_pct'] - bajo['valor_pct']:.1f} puntos porcentuales de "
              f"brecha; {sobre} de 25 departamentos superan el promedio nacional ({nac:.1f} %)")
    sub = "Pobreza monetaria, % de personas · Perú, 2024 · Método oficial del INEI (hogares, factor07 × mieperho)"
    fig, ax = lienzo(titulo, sub, "Estimaciones ponderadas. Departamentos por ubigeo[:2]; Lima (15) y Callao (07) se muestran por "
                     "separado. Las diferencias son descriptivas y no establecen causas.", alto=9.6)
    fig.subplots_adjust(left=0.2)
    y = range(len(d))
    ax.barh(list(y), d["valor_pct"], color=AZUL, height=0.7)
    for yi, v in zip(y, d["valor_pct"]):
        ax.text(v + 0.4, yi, f"{v:.1f}", va="center", fontsize=8.5,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8}, zorder=5)
    ax.axvline(nac, color="#b03a2e", linewidth=1.2, linestyle="--")
    ax.text(nac + 0.3, len(d) - 0.2, f"Nacional {nac:.1f} %", color="#b03a2e", fontsize=9, va="bottom")
    ax.set_yticks(list(y), d["nombre"], fontsize=9)
    ax.set_xlim(0, float(d["valor_pct"].max()) * 1.1)
    ax.set_xlabel("% de personas en pobreza monetaria")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    return guardar(fig, raiz, "enaho2024_pobreza_departamento.png"), d


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):   # acentos correctos también en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    raiz_defecto = Path(__file__).resolve().parents[4]   # .../tarea_4/.claude/skills/graficando-enaho/scripts/graficar.py
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grafico", choices=["area", "sexo", "departamento", "todos"], default="todos")
    ap.add_argument("--raiz", type=Path, default=raiz_defecto, help="carpeta del proyecto (tarea_4)")
    a = ap.parse_args()
    raiz = a.raiz.resolve()
    try:
        ind = cargar(raiz)
        if a.grafico in ("area", "todos"):
            ruta, v = grafico_area(raiz, ind)
            print(f"OK {ruta.relative_to(raiz).as_posix()}: urbana {v['Urbano']:.2f} %, rural {v['Rural']:.2f} % (método oficial, hogares)")
        if a.grafico in ("sexo", "todos"):
            ruta, v = grafico_sexo(raiz, ind)
            print(f"OK {ruta.relative_to(raiz).as_posix()}: mujeres {v['Mujer']:.2f} %, hombres {v['Hombre']:.2f} % "
                  "(por personas, facpob07; puede diferir levemente del método oficial)")
        if a.grafico in ("departamento", "todos"):
            ruta, d = grafico_departamento(raiz, ind)
            print(f"OK {ruta.relative_to(raiz).as_posix()}: 25 departamentos; mayor {d.iloc[-1]['nombre']} "
                  f"{d.iloc[-1]['valor_pct']:.2f} %, menor {d.iloc[0]['nombre']} {d.iloc[0]['valor_pct']:.2f} % (método oficial, hogares)")
    except Falla as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
