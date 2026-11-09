"""Genera salidas/dashboard.html: un panel de un solo archivo para explorar los resultados del agente.

    uv run salidas/generar_dashboard.py

Lee SOLO salidas/indicadores.csv y mapas/comparacion_referencia_2024.csv (ninguna cifra va escrita a mano) y enlaza,
con rutas relativas, las imágenes ya generadas en figuras/ y mapas/. Si falta un archivo, una columna o una categoría,
termina con un error claro y no escribe nada. El HTML lleva su CSS y su JavaScript incrustados: se abre con doble clic.
"""
import html
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salidas" / "dashboard.html"
INDICADORES = RAIZ / "salidas" / "indicadores.csv"
COMPARACION = RAIZ / "mapas" / "comparacion_referencia_2024.csv"
IMAGENES = [   # (archivo, título, pie con método y fuente)
    (RAIZ / "figuras" / "bcrp_PN01273PM_2020-01_2024-12.png", "Inflación a 12 meses, Lima Metropolitana (2020-2024)",
     "Fuente: BCRP, serie PN01273PM (variación % a 12 meses del IPC de Lima Metropolitana), obtenida con la herramienta graficar_serie del MCP."),
    (RAIZ / "figuras" / "enaho2024_pobreza_area.png", "Pobreza monetaria por área (urbano/rural), 2024",
     "Fuente: INEI, ENAHO 2024 (módulos 34 y 02). Método oficial de hogares (factor07 × mieperho)."),
    (RAIZ / "figuras" / "enaho2024_pobreza_sexo.png", "Pobreza monetaria por sexo, 2024",
     "Fuente: INEI, ENAHO 2024. Método por personas (facpob07): puede diferir levemente del oficial de hogares."),
    (RAIZ / "figuras" / "enaho2024_pobreza_departamento.png", "Pobreza monetaria por departamento, 2024",
     "Fuente: INEI, ENAHO 2024. Método oficial de hogares (factor07 × mieperho)."),
    (RAIZ / "mapas" / "pobreza_departamento_2024.png", "Mapa de la pobreza monetaria por departamento, 2024",
     "Fuente: INEI, ENAHO 2024; límites departamentales del GeoJSON del curso. Método oficial de hogares (factor07 × mieperho)."),
]
OFICIAL, PERSONAS = "hogares_factor07_x_mieperho", "personas_facpob07"
ROTULO = {OFICIAL: "método oficial de hogares (factor07 × mieperho)", PERSONAS: "método por personas (facpob07)"}


def error(mensaje: str):
    sys.exit(f"ERROR: {mensaje} No se generó {SALIDA.name}.")


def cargar() -> tuple[pd.DataFrame, pd.DataFrame]:
    for p in (INDICADORES, COMPARACION, *[i[0] for i in IMAGENES]):
        if not p.exists():
            error(f"falta {p.relative_to(RAIZ).as_posix()} (se genera con las skills limpiando-enaho, graficando-enaho y "
                  f"mapeando-enaho, o con el MCP graficar_serie).")
    ind = pd.read_csv(INDICADORES, dtype={"categoria": str})
    comp = pd.read_csv(COMPARACION, dtype={"codigo": str})
    for df, cols, nombre in ((ind, ["indicador", "metodo", "dimension", "categoria", "valor_pct", "n_muestra"], INDICADORES.name),
                             (comp, ["codigo", "nombre", "calculado_pct", "referencia_sesion16_pct", "diferencia_pp", "coincide"], COMPARACION.name)):
        faltan = [c for c in cols if c not in df.columns]
        if faltan:
            error(f"a {nombre} le faltan las columnas {faltan}.")
    if len(comp) != 25:
        error(f"{COMPARACION.name} tiene {len(comp)} departamentos y deben ser 25.")
    return ind, comp


def valor(ind: pd.DataFrame, metodo: str, dimension: str, categoria: str) -> tuple[float, int]:
    f = ind[(ind.indicador == "pobreza monetaria") & (ind.metodo == metodo) & (ind.dimension == dimension) & (ind.categoria == categoria)]
    if len(f) != 1:
        error(f"se esperaba 1 fila de pobreza monetaria para {metodo}/{dimension}/{categoria} y hay {len(f)} en {INDICADORES.name}.")
    return float(f.valor_pct.iloc[0]), int(f.n_muestra.iloc[0])


def tarjeta(titulo: str, ind: pd.DataFrame, metodo: str, dim: str, cat: str) -> str:
    v, n = valor(ind, metodo, dim, cat)
    return (f'<div class="card"><div class="card-t">{html.escape(titulo)}</div><div class="card-v">{v:.1f}<span>%</span></div>'
            f'<div class="card-m">Pobreza monetaria, 2024 · {html.escape(ROTULO[metodo])}<br>Muestra: {n:,} personas</div></div>')


def tabla(ind: pd.DataFrame, comp: pd.DataFrame) -> str:
    of = ind[(ind.indicador == "pobreza monetaria") & (ind.metodo == OFICIAL) & (ind.dimension == "departamento")].set_index("categoria")
    pe = ind[(ind.indicador == "pobreza monetaria") & (ind.metodo == PERSONAS) & (ind.dimension == "departamento")].set_index("categoria")
    if set(of.index) != set(comp.codigo) or set(pe.index) != set(comp.codigo):
        error("los 25 departamentos de indicadores.csv no coinciden con los de la comparación con la sesión 16.")
    filas = []
    for r in comp.sort_values("calculado_pct", ascending=False).itertuples():
        ref = r.referencia_sesion16_pct
        filas.append(
            f'<tr><td data-v="{html.escape(r.nombre)}">{html.escape(r.nombre)}</td><td data-v="{r.codigo}">{r.codigo}</td>'
            f'<td data-v="{r.calculado_pct}">{r.calculado_pct:.1f}</td><td data-v="{pe.loc[r.codigo, "valor_pct"]}">{pe.loc[r.codigo, "valor_pct"]:.1f}</td>'
            f'<td data-v="{ref}">{ref:.1f}</td><td data-v="{r.diferencia_pp}">{r.diferencia_pp:+.2f}</td>'
            f'<td data-v="{int(of.loc[r.codigo, "n_muestra"])}">{int(of.loc[r.codigo, "n_muestra"]):,}</td></tr>')
    return "\n".join(filas)


def figuras() -> str:
    out = []
    for ruta, titulo, pie in IMAGENES:
        rel = Path(os.path.relpath(ruta, SALIDA.parent)).as_posix()   # rutas relativas al dashboard
        out.append(f'<figure><img src="{html.escape(rel)}" alt="{html.escape(titulo)}" loading="lazy">'
                   f'<figcaption><b>{html.escape(titulo)}</b><br>{html.escape(pie)}</figcaption></figure>')
    return "\n".join(out)


PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard Tarea 4</title>
<style>
:root{--bg:#f7f7f5;--fg:#1d1d1b;--mut:#5f5f5a;--card:#fff;--line:#dcdcd6;--acc:#b3401f}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecece8;--mut:#a3a39c;--card:#212120;--line:#3a3a37;--acc:#f08a63}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.2rem;margin:36px 0 10px}
.sub{color:var(--mut);margin:0 0 20px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.card-t{font-weight:600}
.card-v{font-size:2.4rem;font-weight:700;color:var(--acc);line-height:1.1}.card-v span{font-size:1.2rem}.card-m{color:var(--mut);font-size:.82rem;margin-top:6px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card)}th:hover{color:var(--acc)}
th.asc::after{content:" ▲"}th.desc::after{content:" ▼"}.nota{color:var(--mut);font-size:.85rem;margin:8px 0 0}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:16px}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}figure img{width:100%;height:auto;display:block;border-radius:6px;background:#fff}
figcaption{font-size:.82rem;color:var(--mut);margin-top:8px}
</style></head><body><main>
<h1>Agente de investigación socioeconómica: resultados</h1>
<p class="sub">Pobreza monetaria 2024 (INEI, ENAHO 2024) e inflación de Lima (BCRP). Análisis descriptivo, con factores de expansión; no estima relaciones causales.</p>
<h2>Pobreza monetaria, 2024</h2>
<div class="cards">__TARJETAS__</div>
<p class="nota">Cifras de <code>salidas/indicadores.csv</code>. Nacional, urbano y rural: método oficial de hogares. Por sexo: método por personas (puede diferir levemente del oficial).</p>
<h2>Los 25 departamentos (haz clic en una columna para ordenar)</h2>
<div class="wrap"><table id="t"><thead><tr><th>Departamento</th><th>Código</th><th>Oficial hogares (%)</th><th>Personas (%)</th><th>Ref. sesión 16 (%)</th><th>Dif. (pp)</th><th>Muestra (personas)</th></tr></thead>
<tbody>
__FILAS__
</tbody></table></div>
<p class="nota">Fuente: INEI, ENAHO 2024. «Oficial hogares» = factor07 × mieperho (la cifra que se reporta); «Personas» = facpob07 (informativa). La referencia de la sesión 16 está redondeada a 0.1; la diferencia es calculado menos referencia. Lima (15) y Callao (07) van separados.</p>
<h2>Figuras y mapa</h2>
<div class="figs">
__FIGURAS__
</div>
</main>
<script>
const t=document.getElementById('t'),th=t.tHead.rows[0].cells,tb=t.tBodies[0];
[...th].forEach((h,i)=>h.addEventListener('click',()=>{
  const asc=!h.classList.contains('asc');[...th].forEach(x=>x.classList.remove('asc','desc'));h.classList.add(asc?'asc':'desc');
  const val=r=>{const v=r.cells[i].dataset.v,n=parseFloat(v);return (i<2)?v:n};
  [...tb.rows].sort((a,b)=>{const x=val(a),y=val(b);return (typeof x==='string'?x.localeCompare(y,'es'):x-y)*(asc?1:-1)}).forEach(r=>tb.appendChild(r));
}));
</script></body></html>
"""


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ind, comp = cargar()
    tarjetas = "\n".join([
        tarjeta("Nacional", ind, OFICIAL, "nacional", "Perú"),
        tarjeta("Urbano", ind, OFICIAL, "area", "Urbano"),
        tarjeta("Rural", ind, OFICIAL, "area", "Rural"),
        tarjeta("Mujeres", ind, PERSONAS, "sexo", "Mujer"),
        tarjeta("Hombres", ind, PERSONAS, "sexo", "Hombre")])
    texto = PLANTILLA.replace("__TARJETAS__", tarjetas).replace("__FILAS__", tabla(ind, comp)).replace("__FIGURAS__", figuras())
    SALIDA.write_text(texto, encoding="utf-8")
    print(f"Dashboard generado: {SALIDA.relative_to(RAIZ).as_posix()} ({len(texto):,} caracteres, 25 departamentos, {len(IMAGENES)} imágenes)")


if __name__ == "__main__":
    main()
