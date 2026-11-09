"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import calendar
import json
import random
import re
import textwrap
import threading
import time
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path

import httpx
import matplotlib
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError

matplotlib.use("Agg")   # sin ventanas: solo guarda archivos PNG
import matplotlib.dates as mdates  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
FIGURAS = AQUI.parent / "figuras"   # tarea_4/figuras/
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, serie para los datos y graficar_serie para un gráfico. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# ---------------------------------------------------------------------------------------------------------------
# serie y resumen. Piezas internas (empiezan con _) y, al final, las dos herramientas.
# Orden de trabajo: validar el código en el catálogo -> convertir las fechas -> pedir a la API (con reintentos y
# caché) -> traducir los periodos -> devolver. Si algo no cuadra, ToolError: nunca se rellena ni se inventa un dato.
# ---------------------------------------------------------------------------------------------------------------
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}   # setiembre llega como «Set» o «Sep»
INTENTOS = 6            # veces que se reintenta un pedido bloqueado antes de rendirse
PAUSA_MIN = 0.7         # segundos mínimos entre dos pedidos a la API
VIGENCIA_CACHE = 24 * 3600   # un pedido guardado en disco se reutiliza hasta por 24 horas
CACHE = AQUI / "cache"
_candado = threading.Lock()
_ultimo_pedido = [0.0]
_memoria: dict = {}


def _fecha_usuario(texto, frecuencia, es_hasta):
    """Lee la fecha que escribió el usuario según la frecuencia de la serie.

    Devuelve (clave_de_orden, texto_para_la_API). La clave sirve para comprobar que desde <= hasta.
    """
    t = str(texto).strip()
    ejemplos = {"Mensual": "2025-01", "Trimestral": "2025-T1", "Diaria": "2026-10-15", "Anual": "2025"}
    ejemplo = ejemplos.get(frecuencia, "2025")
    if frecuencia == "Anual" and (m := re.fullmatch(r"(\d{4})", t)):
        return (int(m[1]),), m[1]
    if frecuencia == "Mensual" and (m := re.fullmatch(r"(\d{4})-(\d{1,2})", t)) and 1 <= int(m[2]) <= 12:
        return (int(m[1]), int(m[2])), f"{int(m[1])}-{int(m[2])}"
    if frecuencia == "Trimestral" and (m := re.fullmatch(r"(\d{4})-?T?([1-4])", t, re.I)):
        return (int(m[1]), int(m[2])), f"{int(m[1])}-{int(m[2])}"
    if frecuencia == "Diaria":
        if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t):
            try:
                f = date(int(m[1]), int(m[2]), int(m[3]))
            except ValueError:
                raise ToolError(f"La fecha {texto!r} no existe en el calendario.") from None
            return (f.year, f.month, f.day), f.isoformat()
        if (m := re.fullmatch(r"(\d{4})-(\d{1,2})", t)) and 1 <= int(m[2]) <= 12:   # solo año-mes: el mes entero
            a, mes = int(m[1]), int(m[2])
            f = date(a, mes, calendar.monthrange(a, mes)[1] if es_hasta else 1)
            return (f.year, f.month, f.day), f.isoformat()
    raise ToolError(f"Fecha {texto!r} no válida para una serie {frecuencia.lower()}. Use el formato {ejemplo}.")


def _rango_api(frecuencia, desde, hasta):
    """Convierte desde/hasta al formato que pide la API y comprueba que el rango tenga sentido."""
    k1, d = _fecha_usuario(desde, frecuencia, es_hasta=False)
    k2, h = _fecha_usuario(hasta, frecuencia, es_hasta=True)
    if k1 > k2:
        raise ToolError(f"'desde' ({desde}) es posterior a 'hasta' ({hasta}).")
    return d, h


def _json_valido(texto):
    """El JSON de la API si la respuesta lo es; None si es otra cosa (p. ej. la página HTML del bloqueo)."""
    try:
        d = json.loads(texto)
    except ValueError:
        return None
    return d if isinstance(d, dict) and "periods" in d else None


def _pedir(codigo, d, h):
    """Pide la serie a la API del BCRP, con caché y reintentos. Devuelve el JSON crudo de la API.

    - Caché: si el mismo pedido ya salió bien hace menos de 24 h, se reutiliza (memoria y mcp/cache/).
      Solo se guardan pedidos exitosos; un fallo nunca se guarda.
    - Pausa mínima entre pedidos y reintentos con espera creciente, porque la API bloquea al azar los pedidos
      seguidos respondiendo una página HTML en vez de JSON (con el content-type equivocado, así que no se mira).
    - Si tras todos los intentos no hay JSON, ToolError: puede ser un bloqueo o un periodo sin datos.
    """
    clave = f"{codigo}_{d}_{h}"
    archivo = CACHE / f"{clave}.json"
    if clave in _memoria:
        return _memoria[clave]
    if archivo.exists() and time.time() - archivo.stat().st_mtime < VIGENCIA_CACHE:
        crudo = _json_valido(archivo.read_text(encoding="utf-8"))
        if crudo:
            _memoria[clave] = crudo
            return crudo
    url = f"{API}/{codigo}/json/{d}/{h}"
    for intento in range(1, INTENTOS + 1):
        with _candado:   # un pedido a la vez y con pausa, aunque varias herramientas corran en paralelo
            time.sleep(max(0.0, PAUSA_MIN - (time.time() - _ultimo_pedido[0])))
            try:
                r = httpx.get(url, timeout=60)
                crudo = _json_valido(r.content.decode("utf-8", errors="replace"))
            except httpx.HTTPError:
                crudo = None   # error de red: se trata igual que un bloqueo y se reintenta
            _ultimo_pedido[0] = time.time()
        if crudo:
            CACHE.mkdir(exist_ok=True)
            archivo.write_text(json.dumps(crudo, ensure_ascii=False), encoding="utf-8")
            _memoria[clave] = crudo
            return crudo
        time.sleep(intento + random.random())   # espera creciente antes de reintentar
    raise ToolError(f"El BCRP no respondió con datos para {codigo} entre {d} y {h} tras {INTENTOS} intentos: puede ser "
                    f"un límite de pedidos (reintente en unos minutos) o un periodo sin datos. URL: {url}")


def _periodo(nombre, frecuencia):
    """Traduce el nombre de periodo de la API al formato del proyecto: 2025-01, 2026-10-01, 2025-T1 o 2025."""
    n = nombre.strip()
    if frecuencia == "Anual" and re.fullmatch(r"\d{4}", n):
        return n
    if frecuencia == "Trimestral" and (m := re.fullmatch(r"T([1-4])\.(\d{2}|\d{4})", n)):
        a = int(m[2])
        return f"{a if a > 99 else 2000 + a}-T{m[1]}"
    if frecuencia == "Mensual" and (m := re.fullmatch(r"([A-Za-z]{3})\.(\d{4})", n)) and m[1].lower() in MESES:
        return f"{m[2]}-{MESES[m[1].lower()]:02d}"
    if frecuencia == "Diaria" and (m := re.fullmatch(r"(\d{2})\.([A-Za-z]{3})\.(\d{2}|\d{4})", n)) and m[2].lower() in MESES:
        a = int(m[3])
        a = a if a > 99 else (2000 + a if a <= 50 else 1900 + a)   # «26» -> 2026, «97» -> 1997
        return f"{a}-{MESES[m[2].lower()]:02d}-{m[1]}"
    raise ToolError(f"Formato de periodo desconocido en la respuesta del BCRP: {nombre!r} (serie {frecuencia.lower()}).")


def _datos(codigo, desde, hasta):
    """Núcleo compartido por serie y resumen: ficha + datos limpios + URL de la fuente."""
    ficha = _ficha(codigo)   # si el código no existe, falla aquí con un mensaje que lo nombra
    d, h = _rango_api(ficha["frecuencia"], desde, hasta)
    crudo = _pedir(codigo, d, h)
    datos = []
    for p in crudo["periods"]:
        try:
            valor = float(p["values"][0])
        except (ValueError, IndexError, TypeError):
            continue   # «n.d.» (sin dato) u otro valor no numérico: se salta, no se rellena
        datos.append({"periodo": _periodo(p["name"], ficha["frecuencia"]), "valor": valor})
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}.")
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"], "datos": datos,
            "fuente": f"{API}/{codigo}/json/{d}/{h}"}


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos fechas.

    Úsela cuando necesite los valores período por período (para graficar, comparar o revisar una cifra). Si solo
    quiere variaciones, promedios o máximos, use resumen. Primero obtenga el código con buscar_series.
    Fechas según la frecuencia de la serie: mensual "2025-01", trimestral "2025-T1", diaria "2026-10-15"
    (o "2026-10" para el mes entero) y anual "2025". Ejemplo: codigo="PN01271PM", desde="2025-01", hasta="2025-12".
    Devuelve el código, el nombre, la frecuencia, la lista de {periodo, valor} y la URL de la fuente. Los periodos sin
    dato (n.d.) y los fines de semana de las series diarias no aparecen.
    """
    return _datos(codigo, desde, hasta)


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Calcula con Python el resumen de una serie del BCRP entre dos fechas: primero, último, cambio, variación,
    promedio, máximo y mínimo.

    Úsela en vez de calcular a mano cuando le pidan cuánto cambió, cuál fue el promedio o el pico de un indicador.
    Mismas fechas que serie ("2025-12", "2026-10-15", "2025"...). Ejemplo: codigo="PN01273PM", desde="2025-12",
    hasta="2026-09". Ojo: en series que ya vienen en porcentaje (inflación, tasas), `cambio` son puntos porcentuales
    y `variacion_pct` rara vez tiene sentido; en series de nivel (tipo de cambio, reservas) sí lo tiene.
    primero, ultimo, maximo y minimo traen {periodo, valor}. Cite siempre el código, el periodo y la fuente.
    """
    s = _datos(codigo, desde, hasta)
    datos = s["datos"]
    # 1) Todas las cuentas se hacen con los valores originales, sin redondear nada
    primero, ultimo = datos[0], datos[-1]
    maximo = max(datos, key=lambda x: x["valor"])   # si hay empate, el más antiguo
    minimo = min(datos, key=lambda x: x["valor"])
    cambio = ultimo["valor"] - primero["valor"]
    variacion = (ultimo["valor"] / primero["valor"] - 1) * 100 if primero["valor"] else None
    promedio = sum(x["valor"] for x in datos) / len(datos)
    # 2) Se redondea solo al devolver (los valores observados se entregan tal como los publica el BCRP)
    return {"codigo": codigo, "nombre": s["nombre"], "frecuencia": s["frecuencia"], "observaciones": len(datos),
            "primero": primero, "ultimo": ultimo,
            "cambio": round(cambio, 4),
            "variacion_pct": None if variacion is None else round(variacion, 4),
            "promedio": round(promedio, 4),
            "maximo": maximo, "minimo": minimo, "fuente": s["fuente"]}


# ---------------------------------------------------------------------------------------------------------------
# Herramienta propia: graficar_serie. Reutiliza _datos (el mismo núcleo de serie), así que hereda su validación
# del código, su caché y sus errores honestos; aquí solo se dibuja y se guarda el PNG.
# ---------------------------------------------------------------------------------------------------------------
def _unidad(codigo):
    """La unidad de la serie, si el catálogo la trae entre paréntesis: «(S/ por US$)», «(var% mensual)»...

    No se inventa: si el nombre y el grupo no traen paréntesis, devuelve None.
    """
    f = catalogo().query("codigo == @codigo").iloc[0]
    for texto in (f.nombre, f.grupo):
        entre_parentesis = re.findall(r"\(([^()]+)\)", texto)
        if entre_parentesis:
            return entre_parentesis[-1].strip()
    return None


def _fecha_periodo(periodo, frecuencia):
    """Pasa un periodo del proyecto («2025-01», «2025-T1», «2026-10-01», «2025») a una fecha para el eje X."""
    if frecuencia == "Diaria":
        return date.fromisoformat(periodo)
    if frecuencia == "Anual":
        return date(int(periodo), 1, 1)
    if frecuencia == "Trimestral":
        a, q = periodo.split("-T")
        return date(int(a), 3 * (int(q) - 1) + 1, 1)
    a, m = periodo.split("-")
    return date(int(a), int(m), 1)


def _titulo_serie(nombre: str, datos: list[dict]) -> str:
    """Título que dice qué pasó: de qué valor a qué valor y, además, el máximo y el mínimo con su período.
    Todo sale de los datos; así un pico intermedio no queda escondido por los extremos."""
    primero, ultimo = datos[0], datos[-1]
    maximo = max(datos, key=lambda d: d["valor"])
    minimo = min(datos, key=lambda d: d["valor"])
    verbo = "subió" if ultimo["valor"] > primero["valor"] else "bajó" if ultimo["valor"] < primero["valor"] else "no cambió"
    return (f"{nombre}: {verbo} de {primero['valor']:,.2f} en {primero['periodo']} a {ultimo['valor']:,.2f} en "
            f"{ultimo['periodo']} (máx. {maximo['valor']:,.2f} en {maximo['periodo']}; "
            f"mín. {minimo['valor']:,.2f} en {minimo['periodo']})")


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True,
                       "openWorldHint": True})
def graficar_serie(codigo: str, desde: str, hasta: str) -> dict:
    """Dibuja una serie oficial del BCRP, guarda el gráfico como PNG en figuras/ y devuelve la ruta del archivo.

    Úsela cuando pidan un gráfico, la evolución o la tendencia de un indicador (inflación, tipo de cambio,
    reservas...). Para solo cifras use resumen o serie. Primero obtenga el código con buscar_series. Mismas fechas
    que serie. Ejemplo: codigo="PN01273PM", desde="2021-01", hasta="2026-09".
    El gráfico lleva un título que dice qué pasó (de qué valor a qué valor, con el máximo y el mínimo y su período), el nombre y el código de la serie, el
    periodo, la unidad (si el catálogo la indica) y la fuente (BCRP). Devuelve {ruta, ruta_relativa, codigo, nombre,
    periodo, observaciones, unidad, fuente}. Para mostrar el gráfico, cite la ruta.
    """
    s = _datos(codigo, desde, hasta)   # lanza ToolError si el código no existe o no hay datos
    datos, frecuencia = s["datos"], s["frecuencia"]
    unidad = _unidad(codigo)
    etiqueta_unidad = unidad or "unidad no indicada en el catálogo del BCRP"
    x = [_fecha_periodo(d["periodo"], frecuencia) for d in datos]
    y = [d["valor"] for d in datos]
    primero, ultimo = datos[0], datos[-1]
    maximo = max(datos, key=lambda d: d["valor"])
    minimo = min(datos, key=lambda d: d["valor"])
    titulo = _titulo_serie(s["nombre"], datos)
    subtitulo = (f"Serie {codigo} · {frecuencia.lower()} · {primero['periodo']} a {ultimo['periodo']} · "
                 f"{len(datos)} observaciones · Unidad: {etiqueta_unidad}")

    lineas_titulo = textwrap.wrap(titulo, 78)
    extra = 0.045 * max(0, len(lineas_titulo) - 2)   # si el título ocupa más de 2 líneas, se baja el resto
    fig = Figure(figsize=(10, 5.8))
    ax = fig.subplots()
    fig.subplots_adjust(top=0.80 - extra, bottom=0.15, left=0.09, right=0.96)
    ax.plot(x, y, color="#1f5f8b", linewidth=2, marker="o" if len(datos) <= 40 else None, markersize=4)
    if min(y) < 0 < max(y):
        ax.axhline(0, color="#888888", linewidth=0.8)
    rango = (max(y) - min(y)) or abs(y[0]) or 1.0
    ax.set_ylim(min(y) - 0.16 * rango, max(y) + 0.18 * rango)   # margen para que quepan las etiquetas
    etiquetas = {}   # un punto puede ser a la vez el máximo y el último: se rotula una sola vez
    for punto, texto in ((maximo, "máx."), (minimo, "mín."), (ultimo, "último")):
        etiquetas.setdefault(punto["periodo"], (punto, []))[1].append(texto)
    for periodo, (punto, textos) in etiquetas.items():
        debajo = "mín." in textos and "máx." not in textos
        ax.annotate(f"{' y '.join(textos)} {punto['valor']:,.2f}\n({periodo})",
                    (_fecha_periodo(periodo, frecuencia), punto["valor"]), textcoords="offset points",
                    xytext=(0, -24 if debajo else 8), ha="center", fontsize=8, color="#333333")
    ax.set_ylabel(etiqueta_unidad)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.text(0.09, 0.95, textwrap.fill(titulo, 78), fontsize=12.5, fontweight="bold", va="top")
    fig.text(0.09, 0.855 - extra, subtitulo, fontsize=9, color="#444444", va="top")
    fig.text(0.09, 0.03, f"Fuente: BCRP, Estadísticas de series (código {codigo}). Elaboración propia con datos oficiales.",
             fontsize=8, color="#555555")

    ruta = FIGURAS / f"bcrp_{codigo}_{primero['periodo']}_{ultimo['periodo']}.png"
    try:
        FIGURAS.mkdir(exist_ok=True)
        fig.savefig(ruta, dpi=200)
    except OSError as e:
        raise ToolError(f"No se pudo guardar el gráfico en {ruta}: {e}") from None
    return {"ruta": str(ruta), "ruta_relativa": f"figuras/{ruta.name}", "codigo": codigo, "nombre": s["nombre"],
            "periodo": f"{primero['periodo']} a {ultimo['periodo']}", "observaciones": len(datos),
            "unidad": unidad, "fuente": s["fuente"]}


# ---------------------------------------------------------------------------------------------------------------
# Recurso: la ficha de una serie, leída del catálogo local (no llama a la API de datos).
# ---------------------------------------------------------------------------------------------------------------
@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json",
              annotations={"readOnlyHint": True, "idempotentHint": True})
def ficha_serie(codigo: str) -> dict:
    """Ficha descriptiva de una serie del BCRP: nombre, categoría, frecuencia, unidad, desde cuándo hay datos,
    cuándo se actualizó por última vez y la fuente. Ejemplo: bcrp://serie/PN01273PM."""
    try:
        ficha = _ficha(codigo)
    except ToolError as e:
        raise ResourceError(str(e)) from None
    return {**ficha, "unidad": _unidad(codigo) or "no indicada en el catálogo del BCRP",
            "fuente": "Banco Central de Reserva del Perú (BCRP), Estadísticas de series: "
                      "https://estadisticas.bcrp.gob.pe/estadisticas/series/"}


# ---------------------------------------------------------------------------------------------------------------
# Prompt: una receta reutilizable para que Claude arme un informe con las herramientas, sin inventar cifras.
# ---------------------------------------------------------------------------------------------------------------
@mcp.prompt
def informe(tema: str) -> str:
    """Guía a Claude para elaborar un informe breve sobre un indicador del BCRP, citando código, periodo y fuente."""
    return f"""Elabora un informe breve sobre «{tema}» usando solo las herramientas del servidor bcrp.

Sigue estos pasos, en orden:
1. Busca la serie con buscar_series("{tema}"). Si no hay resultados, prueba con menos palabras o con sinónimos. Si
   hay varias series candidatas, elige la más adecuada y di por qué (frecuencia, vigencia, unidad).
2. Confirma qué mide con el recurso bcrp://serie/<código>: nombre, frecuencia, unidad y desde cuándo hay datos.
3. Decide un periodo razonable (por ejemplo, los últimos 12 meses o 5 años) y pide los números con resumen(código,
   desde, hasta). Si necesitas los valores uno por uno, usa serie. No calcules nada a mano: toda variación, promedio,
   máximo o mínimo debe venir de las herramientas.
4. Si ayuda a entender la evolución, genera el gráfico con graficar_serie y cita la ruta del archivo.
5. Presenta el resultado: 3 a 5 hallazgos, cada uno con su cifra, el código de la serie, el periodo exacto y la fuente
   (BCRP, con la URL que devolvió la herramienta). Una tabla con esas columnas funciona bien.
6. Cierra con las limitaciones: qué periodo cubre, si la serie ya viene en porcentaje, y que describir una evolución no
   prueba una causa.

Reglas: no uses cifras que no hayan salido de una herramienta. Si una herramienta falla o no devuelve datos, di
exactamente qué falló y no rellenes con estimaciones."""


if __name__ == "__main__":
    mcp.run()
