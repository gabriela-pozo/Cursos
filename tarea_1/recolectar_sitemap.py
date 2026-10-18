"""Recolecta noticias de El Comercio desde sus sitemaps (datos/raw/acumulado.csv).

Uso:  python recolectar_sitemap.py [--sin-bajada]
Se puede correr varias veces: suma solo noticias nuevas y retoma las bajadas pendientes.
"""
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Cambia el correo por el tuyo (buena practica: identificarte ante el sitio).
UA = "CursoDS-Tarea1/1.0 (proyecto academico; contacto: TU_CORREO@ejemplo.com)"
HEADERS = {"User-Agent": UA}
PAUSA = 1.5
RUTA = Path("datos/raw/acumulado.csv")
SECCIONES = ["politica", "economia", "deporte-total", "tecnologia"]
URL_SITEMAP = "https://elcomercio.pe/sitemap/news/{}/?outputType=xml"

robots = RobotFileParser()
try:
    robots.parse(requests.get("https://elcomercio.pe/robots.txt", headers=HEADERS, timeout=20).text.splitlines())
except requests.RequestException:
    robots.parse([])  # sin robots.txt legible: no hay reglas que aplicar


def get(url):
    """Descarga respetando robots.txt; un reintento. Devuelve bytes o None."""
    if not robots.can_fetch(UA, url):
        return None
    for _ in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            print("  fallo:", e)
            time.sleep(PAUSA)


def limpiar(texto):
    return " ".join((texto or "").split())


def leer_sitemap(seccion):
    xml = get(URL_SITEMAP.format(seccion))
    filas = []
    for entrada in ET.fromstring(xml) if xml else []:
        d = {}
        for e in entrada.iter():
            espacio, _, nombre = e.tag.rpartition("}")
            if "image" not in espacio:  # ignora <image:loc> e <image:title>
                d.setdefault(nombre, (e.text or "").strip())
        if d.get("loc") and d.get("title"):
            ruta_url = [p for p in urlparse(d["loc"]).path.split("/") if p]
            filas.append({
                "titular": limpiar(d["title"]), "bajada": "", "medio": "El Comercio",
                "seccion_original": ruta_url[0] if ruta_url else "", "url": d["loc"],
                "fecha": d.get("publication_date", "")[:10], "feed": seccion,
            })
    return filas


def leer_bajada(url):
    html = get(url)
    time.sleep(PAUSA)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    return limpiar(tag.get("content")) if tag else ""


RUTA.parent.mkdir(parents=True, exist_ok=True)
filas = []
for seccion in SECCIONES:
    print("Leyendo", seccion)
    filas += leer_sitemap(seccion)
    time.sleep(PAUSA)

previo = pd.read_csv(RUTA) if RUTA.exists() else pd.DataFrame()
df = pd.concat([previo, pd.DataFrame(filas)]).drop_duplicates("url").reset_index(drop=True)
if df.empty:
    sys.exit("No se obtuvo nada.")
df["bajada"] = df["bajada"].fillna("")

if "--sin-bajada" not in sys.argv:
    pendientes = df.index[df["bajada"] == ""]
    print(f"Bajadas por pedir: {len(pendientes)} (~{len(pendientes) * PAUSA / 60:.0f} min)")
    for n, i in enumerate(pendientes, 1):
        df.loc[i, "bajada"] = leer_bajada(df.loc[i, "url"])
        if n % 25 == 0:  # guardado parcial: si cortas, retomas despues
            df.to_csv(RUTA, index=False)
            print(f"  {n}/{len(pendientes)}")

df.to_csv(RUTA, index=False)
print(f"\nTotal acumulado: {len(df)} | Bajadas vacias: {(df['bajada'] == '').sum()}")
print(df.groupby(["feed", "seccion_original"]).size().to_string())
