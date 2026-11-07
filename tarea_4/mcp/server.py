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
import threading
import time
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
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
    primero, ultimo = datos[0], datos[-1]
    maximo = max(datos, key=lambda x: x["valor"])   # si hay empate, el más antiguo
    minimo = min(datos, key=lambda x: x["valor"])
    return {"codigo": codigo, "nombre": s["nombre"], "frecuencia": s["frecuencia"], "observaciones": len(datos),
            "primero": primero, "ultimo": ultimo,
            "cambio": round(ultimo["valor"] - primero["valor"], 4),
            "variacion_pct": round((ultimo["valor"] / primero["valor"] - 1) * 100, 4) if primero["valor"] else None,
            "promedio": round(sum(x["valor"] for x in datos) / len(datos), 4),
            "maximo": maximo, "minimo": minimo, "fuente": s["fuente"]}


# TODO 3 · Una herramienta suya, bien descrita. Ideas:
#   - comparar_paises con la API del Banco Mundial, que tampoco pide clave:
#     https://api.worldbank.org/v2/country/PER;CHL;COL/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2015:2025
#   - correlacion(codigo_a, codigo_b, desde, hasta)
#   - grafico(codigo, desde, hasta) que guarde un PNG en salidas/ y devuelva la ruta

# TODO 4 · Un recurso, por ejemplo la plantilla bcrp://serie/{codigo} con la ficha de la serie.

# TODO 5 · Un prompt, por ejemplo informe(tema) que pida citar el código y el periodo de cada cifra.


if __name__ == "__main__":
    mcp.run()
