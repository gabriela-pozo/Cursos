"""Genera informes/trazabilidad.md: todas las cifras que puede usar el informe y de dónde sale cada una.

    uv run informes/generar_trazabilidad.py

Fuentes (nada se escribe a mano ni se toma de memoria):
  - BCRP: las respuestas de las herramientas MCP (buscar_series, recurso bcrp://serie/{codigo}, resumen, serie y
    graficar_serie) tal como quedaron en el registro de la ejecución de Claude Code: evidencias_ia/integracion/ejecucion.jsonl.
    NO se vuelve a consultar el BCRP para obtener estas cifras. Si el registro no se puede leer o falta una llamada, el
    script termina con un error que lo dice.
  - ENAHO: salidas/indicadores.csv, salidas/validacion.txt y mapas/comparacion_referencia_2024.csv, generados por las
    skills limpiando-enaho y mapeando-enaho dentro de esa misma ejecución.
Además hace una VERIFICACIÓN INDEPENDIENTE, declarada como tal: consulta la API del BCRP directamente (sin pasar por el
servidor MCP) y recalcula la pobreza desde los microdatos .dta con otro código distinto del de limpiando-enaho, y
compara. Si algo no coincide o no se puede verificar, termina con error.
Los valores derivados se calculan con los valores sin redondear y se muestran con 2 y con 1 decimal.
"""
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
REGISTRO = RAIZ / "evidencias_ia" / "integracion" / "ejecucion.jsonl"
SERIE = "PN01273PM"
DESDE, HASTA = "2020-01", "2024-12"
OFICIAL = "hogares_factor07_x_mieperho"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"


class Falla(Exception):
    """Error explícito que detiene el proceso."""


# ------------------------------------------------------------------------------------------- lectura del registro
def texto_de(contenido) -> str:
    if isinstance(contenido, str):
        return contenido
    return "".join(x.get("text", "") for x in (contenido or []) if isinstance(x, dict))


def leer_registro(ruta: Path) -> list[dict]:
    """Devuelve las llamadas a herramientas en orden, con su resultado enlazado por identificador."""
    if not ruta.exists():
        raise Falla(f"No existe el registro de la ejecución: {ruta}")
    llamadas, por_id = [], {}
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            raise Falla(f"El registro no se pudo leer: la línea {n} no es JSON válido.") from None
        mensaje = ev.get("message") or {}
        for bloque in mensaje.get("content", []) if isinstance(mensaje.get("content"), list) else []:
            if ev.get("type") == "assistant" and bloque.get("type") == "tool_use":
                c = {"n": len(llamadas) + 1, "id": bloque["id"], "nombre": bloque["name"], "args": bloque["input"],
                     "resultado": None, "error": None}
                llamadas.append(c)
                por_id[c["id"]] = c
            elif ev.get("type") == "user" and bloque.get("type") == "tool_result" and bloque.get("tool_use_id") in por_id:
                c = por_id[bloque["tool_use_id"]]
                c["resultado"], c["error"] = texto_de(bloque.get("content")), bool(bloque.get("is_error"))
    if not llamadas:
        raise Falla("El registro no contiene ninguna llamada a herramientas: no se pudo leer o está vacío.")
    return llamadas


def llamada(llamadas, nombre, **donde) -> dict:
    """La primera llamada exitosa a una herramienta, opcionalmente filtrada por argumentos."""
    for c in llamadas:
        if c["nombre"] == nombre and all(c["args"].get(k) == v for k, v in donde.items()):
            if c["resultado"] is None or c["error"]:
                raise Falla(f"La llamada {nombre} {donde} del registro no tiene un resultado válido: {str(c['resultado'])[:120]}")
            return c
    raise Falla(f"El registro no contiene una llamada a {nombre} {donde}. Declarar en el informe que no se ejecutó.")


def json_de(c) -> dict | list:
    try:
        return json.loads(c["resultado"])
    except json.JSONDecodeError:
        raise Falla(f"El resultado de {c['nombre']} no se pudo leer como JSON: {c['resultado'][:120]!r}") from None


# ------------------------------------------------------------------------------------------- tabla de cifras
class Cifras:
    def __init__(self):
        self.secciones = []   # (titulo, nota, filas)

    def seccion(self, titulo: str, nota: str = ""):
        self.secciones.append([titulo, nota, []])

    def fila(self, ident: str, cifra: str, valor, origen: str, d2=True):
        """valor numérico -> se muestra con 2 y con 1 decimal; texto o entero -> tal cual."""
        if isinstance(valor, float):
            v2, v1 = f"{valor:.2f}", f"{valor:.1f}"
        else:
            v2, v1 = (f"{valor:,}" if isinstance(valor, int) else str(valor)), "–"
        self.secciones[-1][2].append((ident, cifra, v2, v1, origen))

    def markdown(self) -> str:
        out = []
        for titulo, nota, filas in self.secciones:
            out += [f"\n## {titulo}\n"]
            if nota:
                out += [nota + "\n"]
            out += ["| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |", "|---|---|---|---|---|"]
            out += [f"| {i} | {c} | {a} | {b} | {o} |" for i, c, a, b, o in filas]
        return "\n".join(out)


def pct(x: float) -> str:
    return f"{x:.2f}"


# ------------------------------------------------------------------------------------------- BCRP desde el registro
def cifras_bcrp(llamadas, cif: Cifras) -> dict:
    busq = llamada(llamadas, "mcp__bcrp__buscar_series")
    res_busq = json_de(busq)
    lista = res_busq["result"] if isinstance(res_busq, dict) else res_busq
    if SERIE not in [x["codigo"] for x in lista]:
        raise Falla(f"buscar_series no devolvió {SERIE}.")
    recurso = llamada(llamadas, "ReadMcpResourceTool", uri=f"bcrp://serie/{SERIE}")
    ficha = json.loads(json_de(recurso)["contents"][0]["text"])
    rs = json_de(llamada(llamadas, "mcp__bcrp__resumen", codigo=SERIE, desde=DESDE, hasta=HASTA))
    sr_call = llamada(llamadas, "mcp__bcrp__serie", codigo=SERIE, desde=DESDE, hasta=HASTA)
    sr = json_de(sr_call)
    gr = json_de(llamada(llamadas, "mcp__bcrp__graficar_serie", codigo=SERIE, desde=DESDE, hasta=HASTA))
    datos = sr["datos"]
    if datos[0]["periodo"] != DESDE or datos[-1]["periodo"] != HASTA:
        raise Falla(f"La serie no cubre {DESDE} a {HASTA}: {datos[0]['periodo']} a {datos[-1]['periodo']}.")

    # coherencia entre dos herramientas distintas sobre los mismos datos
    mx = max(datos, key=lambda d: d["valor"])
    mn = min(datos, key=lambda d: d["valor"])
    for nombre, a, b in (("primero", rs["primero"], datos[0]), ("ultimo", rs["ultimo"], datos[-1]),
                         ("maximo", rs["maximo"], mx), ("minimo", rs["minimo"], mn)):
        if a != b:
            raise Falla(f"resumen y serie no coinciden en {nombre}: {a} vs {b}.")
    if rs["observaciones"] != len(datos):
        raise Falla("resumen y serie no coinciden en el número de observaciones.")

    h = f"{sr['fuente']}"
    cif.seccion("A. Inflación a 12 meses, Lima Metropolitana (BCRP)",
                f"Serie **{SERIE}**: {sr['nombre']}. Frecuencia {sr['frecuencia'].lower()}. Fuente: BCRP, {h}. "
                "Las cifras salen de las respuestas de las herramientas MCP en el registro de la ejecución. "
                "Es una tasa a 12 meses ya expresada en %, por eso el cambio entre dos fechas se mide en puntos porcentuales.")
    o_res = f"`resumen` (llamada {resumen_n(llamadas, 'mcp__bcrp__resumen')}, {h})"
    o_ser = f"`serie` (llamada {resumen_n(llamadas, 'mcp__bcrp__serie')})"
    cif.fila("B01", "Observaciones mensuales", rs["observaciones"], o_res)
    cif.fila("B02", f"Primer dato del período ({rs['primero']['periodo']})", float(rs["primero"]["valor"]), o_res)
    cif.fila("B03", f"Último dato del período ({rs['ultimo']['periodo']})", float(rs["ultimo"]["valor"]), o_res)
    cif.fila("B04", f"Máximo del período ({rs['maximo']['periodo']})", float(rs["maximo"]["valor"]), o_res)
    cif.fila("B05", f"Mínimo del período ({rs['minimo']['periodo']})", float(rs["minimo"]["valor"]), o_res)
    cif.fila("B06", "Promedio simple de las 60 tasas mensuales", float(rs["promedio"]), o_res)
    cif.fila("B07", "Cambio entre el primer y el último dato, en puntos porcentuales", float(rs["cambio"]), o_res)
    deriv = "calculado por este script con los valores de `serie` sin redondear"
    cif.fila("B08", "Caída del máximo al último dato, en puntos porcentuales", mx["valor"] - datos[-1]["valor"], deriv)
    cif.fila("B09", "Amplitud (máximo menos mínimo), en puntos porcentuales", mx["valor"] - mn["valor"], deriv)
    cif.fila("B10", "Meses entre el máximo y el último dato", len(datos) - 1 - datos.index(mx), deriv)
    por_anio = {}
    for d in datos:
        por_anio.setdefault(d["periodo"][:4], []).append(d["valor"])
    anios = sorted(por_anio)
    cif.seccion("A2. Inflación a 12 meses: diciembre de cada año y promedio anual",
                "Valores de `serie` (diciembre) y promedio simple de las tasas mensuales de cada año (calculado por este script).")
    for i, a in enumerate(anios):
        dic = next(d for d in datos if d["periodo"] == f"{a}-12")
        cif.fila(f"B{11 + i}", f"Año {a}: tasa de diciembre ({a}-12)", float(dic["valor"]), o_ser + " · diciembre")
        cif.fila(f"B{16 + i}", f"Año {a}: promedio de sus 12 tasas mensuales", sum(por_anio[a]) / len(por_anio[a]), deriv)
    cif.seccion("A3. Ficha de la serie y gráfico",
                "Ficha leída con el recurso MCP `bcrp://serie/PN01273PM`; gráfico generado por `graficar_serie`.")
    cif.fila("R01", "Inicio de la serie en el catálogo", ficha["inicio"], f"recurso `bcrp://serie/{SERIE}` (llamada {resumen_n(llamadas, 'ReadMcpResourceTool')})")
    cif.fila("R02", "Última actualización de la serie en el catálogo", ficha["actualizada"], "recurso `bcrp://serie/PN01273PM`")
    cif.fila("R03", "Gráfico del BCRP generado", gr["ruta_relativa"], f"`graficar_serie` (llamada {resumen_n(llamadas, 'mcp__bcrp__graficar_serie')})")
    return {"datos": datos, "rs": rs, "gr": gr}


def resumen_n(llamadas, nombre) -> int:
    return next(c["n"] for c in llamadas if c["nombre"] == nombre)


# ------------------------------------------------------------------------------------------- ENAHO desde los archivos
def cifras_enaho(cif: Cifras) -> dict:
    ind = pd.read_csv(RAIZ / "salidas" / "indicadores.csv", dtype={"categoria": str})
    ref = pd.read_csv(RAIZ / "mapas" / "comparacion_referencia_2024.csv", dtype={"codigo": str})
    val = (RAIZ / "salidas" / "validacion.txt").read_text(encoding="utf-8")

    def fila(dim, cat, ind_nombre="pobreza monetaria"):
        d = ind[(ind["indicador"] == ind_nombre) & (ind["metodo"] == OFICIAL) & (ind["dimension"] == dim) & (ind["categoria"] == cat)]
        if len(d) != 1:
            raise Falla(f"indicadores.csv no trae una fila única para {ind_nombre}/{dim}/{cat}.")
        return d.iloc[0]
    nac, urb, rur, ext = fila("nacional", "Perú"), fila("area", "Urbano"), fila("area", "Rural"), fila("nacional", "Perú", "pobreza extrema")
    o = "`salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho)"
    cif.seccion("C. Pobreza monetaria 2024 por área (ENAHO, método oficial del INEI)",
                "Estimaciones ponderadas con `factor07 × mieperho`, generadas por la skill `limpiando-enaho`. Unidad: % de personas.")
    cif.fila("E01", "Pobreza monetaria nacional", float(nac["valor_pct"]), o + " · nacional/Perú")
    cif.fila("E02", "Pobreza monetaria urbana", float(urb["valor_pct"]), o + " · area/Urbano")
    cif.fila("E03", "Pobreza monetaria rural", float(rur["valor_pct"]), o + " · area/Rural")
    deriv = "calculado por este script con los valores de `indicadores.csv` sin redondear"
    cif.fila("E04", "Diferencia rural menos urbana, en puntos porcentuales", rur["valor_pct"] - urb["valor_pct"], deriv)
    cif.fila("E05", "Razón rural / urbana (veces)", rur["valor_pct"] / urb["valor_pct"], deriv)
    cif.fila("E06", "Hogares de la muestra, área urbana", int(urb["n_muestra"]), o)
    cif.fila("E07", "Hogares de la muestra, área rural", int(rur["n_muestra"]), o)
    cif.fila("E08", "Pobreza extrema nacional", float(ext["valor_pct"]), o + " · pobreza extrema")

    dep = ind[(ind["indicador"] == "pobreza monetaria") & (ind["metodo"] == OFICIAL) & (ind["dimension"] == "departamento")]
    dep = dep.merge(ref[["codigo", "nombre"]], left_on="categoria", right_on="codigo", validate="1:1")
    if len(dep) != 25:
        raise Falla(f"Se esperaban 25 departamentos y hay {len(dep)}.")
    dep = dep.sort_values("valor_pct", ascending=False).reset_index(drop=True)
    alto, bajo = dep.iloc[0], dep.iloc[-1]
    od = "`salidas/indicadores.csv` · departamento (método oficial)"
    cif.seccion("D. Pobreza monetaria 2024 por departamento (ENAHO, método oficial del INEI)",
                "Departamentos por `ubigeo[:2]`; Lima (15) y Callao (07) separados. Unidad: % de personas.")
    cif.fila("E09", "Departamentos con dato", len(dep), od)
    cif.fila("E10", f"Mayor pobreza: {alto['nombre']} (código {alto['categoria']})", float(alto["valor_pct"]), od)
    cif.fila("E11", f"Menor pobreza: {bajo['nombre']} (código {bajo['categoria']})", float(bajo["valor_pct"]), od)
    cif.fila("E12", "Brecha entre el mayor y el menor, en puntos porcentuales", alto["valor_pct"] - bajo["valor_pct"], deriv)
    sobre = int((dep["valor_pct"] > nac["valor_pct"]).sum())
    cif.fila("E13", "Departamentos con pobreza mayor que el promedio nacional", sobre, deriv)
    cif.fila("E14", "Departamentos con pobreza menor o igual que el promedio nacional", len(dep) - sobre, deriv)
    cif.fila("E15", "Departamentos con pobreza mayor que la rural nacional", int((dep["valor_pct"] > rur["valor_pct"]).sum()), deriv)
    cif.fila("E16", "Departamentos con pobreza menor que la urbana nacional", int((dep["valor_pct"] < urb["valor_pct"]).sum()), deriv)
    for cod, ident in (("15", "E17"), ("07", "E18")):
        f = dep[dep["categoria"] == cod].iloc[0]
        cif.fila(ident, f"{f['nombre']} (código {cod})", float(f["valor_pct"]), od)
    cif.seccion("D2. Los 25 departamentos, de mayor a menor pobreza",
                "Una fila por departamento (`salidas/indicadores.csv`); la columna ID lleva el código territorial.")
    for _, f in dep.iterrows():
        cif.fila(f"D{f['categoria']}", f"{f['nombre']} (hogares de la muestra: {int(f['n_muestra']):,})", float(f["valor_pct"]), od)

    # validación de la skill de limpieza
    def de(patron, texto=val):
        m = re.search(patron, texto)
        if not m:
            raise Falla(f"No encontré en validacion.txt: {patron}")
        return m
    resid = de(r"Residentes habituales\s*\n\s*obtenido: ([\d,]+) de ([\d,]+) filas")
    resumen_v = de(r"RESUMEN: (\d+) APROBADAS, (\d+) FALLIDAS")
    if resumen_v[2] != "0" or "TODAS LAS VERIFICACIONES ESENCIALES APROBADAS" not in val:
        raise Falla("validacion.txt registra verificaciones fallidas: no se generan cifras con datos no validados.")
    hog = de(r"Sumaria: número de hogares\s*\n\s*obtenido: ([\d,]+)")
    ov = "`salidas/validacion.txt` (skill `limpiando-enaho`)"
    cif.seccion("E. Validación de la base y comparación con la referencia de la sesión 16")
    cif.fila("V01", "Residentes habituales", int(resid[1].replace(",", "")), ov)
    cif.fila("V02", "Filas del módulo 02 (miembros)", int(resid[2].replace(",", "")), ov)
    cif.fila("V03", "Hogares de la sumaria", int(hog[1].replace(",", "")), ov)
    cif.fila("V04", "Verificaciones aprobadas", int(resumen_v[1]), ov)
    cif.fila("V05", "Verificaciones fallidas", int(resumen_v[2]), ov)
    cif.fila("V06", "Departamentos que coinciden con la referencia de la sesión 16", int(ref["coincide"].sum()), "`mapas/comparacion_referencia_2024.csv` (skill `mapeando-enaho`)")
    cif.fila("V07", "Diferencia máxima con la referencia, en puntos porcentuales", f"{float(ref['diferencia_pp'].abs().max()):.3f}", "`mapas/comparacion_referencia_2024.csv` (3 decimales)")
    cif.fila("V08", "Tolerancia por el redondeo de la referencia, en puntos porcentuales", "0.05", "constante de `mapear.py` (la referencia está a 1 decimal)")
    return {"nac": nac, "urb": urb, "rur": rur, "dep": dep}


# ------------------------------------------------------------------------------------------- orquestación
def orquestacion(llamadas, cif: Cifras):
    mcp = [c for c in llamadas if c["nombre"].startswith("mcp__bcrp__") or c["nombre"] == "ReadMcpResourceTool"]
    skills = [c for c in llamadas if c["nombre"] == "Skill"]
    nombres_mcp = sorted({c["nombre"].replace("mcp__bcrp__", "bcrp:") for c in mcp})
    nombres_skills = sorted({c["args"]["skill"] for c in skills})
    ls = next((c for c in llamadas if c["nombre"] == "Bash" and "ls salidas" in c["args"].get("command", "")), None)
    sin_parquet = bool(ls and ls["resultado"] and "personas_2024.parquet" not in ls["resultado"])
    cif.seccion("F. Orquestación: lo que hizo Claude Code en una sola ejecución",
                "Del registro `evidencias_ia/integracion/ejecucion.jsonl`. Las skills se activaron por la pregunta en lenguaje natural.")
    cif.fila("O01", "Herramientas MCP distintas usadas", len(nombres_mcp), "; ".join(nombres_mcp))
    cif.fila("O02", "Skills distintas usadas", len(nombres_skills), "; ".join(nombres_skills))
    cif.fila("O03", "Al empezar, salidas/personas_2024.parquet no existía", "sí" if sin_parquet else "NO COMPROBADO", "resultado de `ls` en la llamada " + (str(ls["n"]) if ls else "?"))
    cif.fila("O04", "Llamadas a herramientas en total", len(llamadas), "registro de la ejecución")
    return nombres_mcp, nombres_skills


def cuadro_llamadas(llamadas) -> str:
    out = ["\n## G. Llamadas a herramientas, en orden\n", "| # | Herramienta | Argumentos | Resultado (inicio) |", "|---|---|---|---|"]
    for c in llamadas:
        arg = json.dumps(c["args"], ensure_ascii=False)
        arg = (arg[:110] + "…") if len(arg) > 110 else arg
        res = re.sub(r"\s+", " ", (c["resultado"] or "").replace("|", "/"))[:90]
        out.append(f"| {c['n']} | `{c['nombre']}` | `{arg.replace('|', '/')}` | {res} |")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- verificación independiente
def bcrp_crudo(desde: str, hasta: str, intentos: int = 8) -> list[dict]:
    """Consulta la API del BCRP directamente con urllib (User-Agent por defecto), sin pasar por el servidor MCP."""
    url = f"{API}/{SERIE}/json/{desde}/{hasta}"
    for i in range(intentos):
        try:
            texto = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", errors="replace")
            return json.loads(texto)["periods"]
        except (ValueError, KeyError, OSError):
            time.sleep(6 + i)   # la API bloquea los pedidos seguidos con una página HTML: se espera y se reintenta
    raise Falla(f"La API del BCRP no respondió con datos tras {intentos} intentos; la verificación independiente NO se pudo hacer.")


def verificacion(bcrp, enaho, cif: Cifras):
    MES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
    crudo = bcrp_crudo("2020-1", "2024-12")
    por_periodo = {}
    for p in crudo:
        mes, anio = p["name"].split(".")
        por_periodo[f"{anio}-{MES[mes]:02d}"] = float(p["values"][0])
    herramienta = {d["periodo"]: d["valor"] for d in bcrp["datos"]}
    if set(herramienta) != set(por_periodo):
        raise Falla("La API cruda y la herramienta `serie` no devuelven los mismos periodos.")
    dif_max = max(abs(herramienta[k] - por_periodo[k]) for k in herramienta)

    # microdatos: otro código, otra ruta (solo pandas), sin usar limpiar.py
    sum_dta = next((RAIZ / "datos").rglob("sumaria-2024.dta"), None)
    if sum_dta is None:
        raise Falla("Falta datos/.../sumaria-2024.dta para la verificación independiente de ENAHO.")
    h = pd.read_stata(sum_dta, convert_categoricals=False, columns=["pobreza", "factor07", "mieperho", "estrato", "ubigeo"])
    h["w"] = h["factor07"].astype("float64") * h["mieperho"]
    h["p"] = h["pobreza"] <= 2

    def tasa(m):
        return float(100 * (h.loc[m, "w"] * h.loc[m, "p"]).sum() / h.loc[m, "w"].sum())
    indep = {"urbana": tasa(h["estrato"] <= 5), "rural": tasa(h["estrato"] > 5), "nacional": tasa(h["w"] > 0)}
    dep = enaho["dep"].set_index("categoria")
    for cod in ("06", "11", "15", "07"):
        indep[cod] = tasa(h["ubigeo"].str[:2] == cod)
    reportado = {"urbana": enaho["urb"]["valor_pct"], "rural": enaho["rur"]["valor_pct"], "nacional": enaho["nac"]["valor_pct"],
                 **{c: dep.loc[c, "valor_pct"] for c in ("06", "11", "15", "07")}}

    filas = [("BCRP", f"Inflación a 12 meses, {bcrp['rs']['primero']['periodo']}", bcrp["rs"]["primero"]["valor"], por_periodo["2020-01"], 1e-9),
             ("BCRP", f"Inflación a 12 meses, {bcrp['rs']['maximo']['periodo']} (máximo)", bcrp["rs"]["maximo"]["valor"], por_periodo[bcrp["rs"]["maximo"]["periodo"]], 1e-9),
             ("BCRP", f"Inflación a 12 meses, {bcrp['rs']['ultimo']['periodo']}", bcrp["rs"]["ultimo"]["valor"], por_periodo["2024-12"], 1e-9),
             ("BCRP", "Promedio simple de los 60 meses", bcrp["rs"]["promedio"], sum(por_periodo.values()) / len(por_periodo), 1e-4)]
    for c, nombre in (("nacional", "Pobreza nacional"), ("urbana", "Pobreza urbana"), ("rural", "Pobreza rural"),
                      ("06", "Pobreza en el departamento 06 (Cajamarca)"), ("11", "Pobreza en el departamento 11 (Ica)"),
                      ("15", "Pobreza en el departamento 15 (Lima)"), ("07", "Pobreza en el departamento 07 (Callao)")):
        filas.append(("ENAHO", nombre, float(reportado[c]), indep[c], 1e-4))
    cif.seccion("H. Verificación independiente de cifras",
                "**Declarado:** estas comparaciones SÍ consultan la fuente de nuevo, por un camino distinto del que usó el agente. "
                "BCRP: pedido directo a la API (`urllib`, sin pasar por el servidor MCP). ENAHO: recálculo con pandas desde "
                "`sumaria-2024.dta` (`factor07 × mieperho`), sin usar `limpiar.py`. Las cifras del informe vienen de las secciones "
                "anteriores, no de esta.")
    mal = []
    for i, (fuente, nombre, a, b, tol) in enumerate(filas, 1):
        ok = abs(a - b) <= tol
        if not ok:
            mal.append(nombre)
        cif.fila(f"X{i:02d}", f"[{fuente}] {nombre}: valor de las herramientas / valor independiente / diferencia / coincide",
                 f"{a:.6f} / {b:.6f} / {abs(a - b):.6f} / {'sí' if ok else 'NO'}",
                 "API cruda del BCRP" if fuente == "BCRP" else "recálculo desde sumaria-2024.dta")
    cif.fila("X20", "Periodos de la serie comparados uno a uno con la API cruda", len(herramienta), "API cruda vs `serie`")
    cif.fila("X21", "Diferencia máxima entre `serie` y la API cruda en esos periodos", f"{dif_max:.6f}", "API cruda vs `serie`")
    if mal or dif_max > 1e-9:
        raise Falla(f"La verificación independiente encontró diferencias en: {mal} (máx. serie vs API cruda {dif_max}).")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):   # acentos correctos también en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    try:
        llamadas = leer_registro(REGISTRO)
        cif = Cifras()
        nm, ns = orquestacion(llamadas, cif)
        if len(nm) < 2 or len(ns) < 2:
            raise Falla(f"La ejecución debe usar al menos 2 herramientas MCP y 2 skills distintas; usó {len(nm)} y {len(ns)}.")
        bcrp = cifras_bcrp(llamadas, cif)
        enaho = cifras_enaho(cif)
        verificacion(bcrp, enaho, cif)
        cif.seccion("I. Constantes del planteamiento", "Números que fija la pregunta de investigación; no son resultados.")
        cif.fila("K01", "Años de la pregunta (inicio y fin)", "2020 y 2024", "pregunta de investigación acordada")
        cif.fila("K02", "Horizonte de la tasa de inflación, en meses", 12, "definición de la serie `PN01273PM`")
        cif.fila("K03", "Departamentos del Perú en el mapa", 25, "GeoJSON departamental (`FIRST_IDDP` 01 a 25)")
        cif.fila("K04", "Año de la ENAHO usada", "2024", "módulos 34 y 02 de la ENAHO 2024")
    except Falla as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    cab = ["# Trazabilidad de cifras", "",
           "Generado por `informes/generar_trazabilidad.py`. **Toda cifra del informe debe estar en este archivo**: "
           "`informes/verificar_informe.py` falla si el informe contiene un número que no aparece aquí.", "",
           f"- Registro de la ejecución: `evidencias_ia/integracion/ejecucion.jsonl` (sha256 `{sha(REGISTRO)}`)",
           f"- Indicadores ENAHO: `salidas/indicadores.csv` (sha256 `{sha(RAIZ / 'salidas' / 'indicadores.csv')}`)",
           "- Las cifras del BCRP se tomaron de las respuestas de las herramientas MCP en ese registro; no se reconsultó el BCRP "
           "para obtenerlas. Solo la sección H consulta las fuentes de nuevo, y lo declara.",
           "- Los valores derivados se calculan con los valores sin redondear: restar a mano los valores redondeados puede "
           "diferir en una centésima.",
           "- Limitación de esta verificación: acepta un número del informe si aparece en cualquier parte de este archivo; "
           "no comprueba que se use en el contexto correcto. Eso lo revisa la lectura del informe."]
    (RAIZ / "informes" / "trazabilidad.md").write_text("\n".join(cab) + "\n" + cif.markdown() + "\n" + cuadro_llamadas(llamadas) + "\n", encoding="utf-8")
    print(f"OK informes/trazabilidad.md: {sum(len(s[2]) for s in cif.secciones)} cifras; "
          f"MCP distintas: {len(nm)} ({', '.join(nm)}); skills distintas: {len(ns)} ({', '.join(ns)}); verificación independiente aprobada.")


if __name__ == "__main__":
    main()
