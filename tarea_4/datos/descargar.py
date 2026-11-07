"""Descarga los datos de la Tarea 4 a la carpeta datos/ (que Git ignora).

    uv run datos/descargar.py

Baja de ENAHO 2024 los módulos 34 (sumaria) y 02 (miembros) en formato STATA, y el GeoJSON
departamental del repositorio del curso. Los zip se descomprimen en datos/966-Modulo34/ y
datos/966-Modulo02/. Si un archivo ya existe y es válido, no se vuelve a bajar.
Solo usa la biblioteca estándar. Si una descarga falla, el script termina con error: no inventa datos.
Si el INEI bloquea la descarga automática, bájelos a mano desde los enlaces de ZIPS/GEOJSON (más abajo) y
descomprima cada zip en datos/966-ModuloXX/.
"""
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DATOS = Path(__file__).resolve().parent
INEI = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA"
GEO = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
       "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson")

ZIPS = {
    "966-Modulo34.zip": f"{INEI}/966-Modulo34.zip",
    "966-Modulo02.zip": f"{INEI}/966-Modulo02.zip",
}
GEOJSON = ("peru_departamental_simple.geojson", GEO)


def bajar(url: str, destino: Path) -> None:
    """Descarga url a destino (por un archivo temporal, para no dejar archivos a medias)."""
    print(f"Bajando {url}")
    tmp = destino.with_suffix(destino.suffix + ".part")
    # User-Agent por defecto de Python: no se disfraza la descarga. Si el INEI la bloquea, ver README (descarga manual).
    with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(destino)
    print(f"  -> {destino.name}: {destino.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    DATOS.mkdir(exist_ok=True)
    for nombre, url in ZIPS.items():
        destino = DATOS / nombre
        if not (destino.exists() and zipfile.is_zipfile(destino)):
            bajar(url, destino)
        if not zipfile.is_zipfile(destino):
            raise SystemExit(f"ERROR: {nombre} no es un zip válido (¿el INEI devolvió una página de error?).")
        carpeta = DATOS / destino.stem
        with zipfile.ZipFile(destino) as z:
            z.extractall(carpeta)
        print(f"  extraído en {carpeta.name}/: {len(list(carpeta.rglob('*.dta')))} archivo(s) .dta")

    nombre, url = GEOJSON
    destino = DATOS / nombre
    if not destino.exists():
        bajar(url, destino)

    faltan = [n for n in (*ZIPS, GEOJSON[0]) if not (DATOS / n).exists()]
    if faltan:
        raise SystemExit(f"ERROR: faltan archivos: {faltan}")
    print("Listo: datos en", DATOS)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # red caída, servidor del INEI no disponible, etc.
        print(f"ERROR en la descarga: {e}", file=sys.stderr)
        sys.exit(1)
