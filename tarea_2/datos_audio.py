"""Descarga clips nuevos de espanol peruano (OpenSLR 73) para el corpus de audio.

OpenSLR 73 es "Crowdsourced high-quality Peruvian Spanish speech data set"
(Google, CC BY-SA 4.0). Cada clip trae su transcripcion oficial, que NO es la
transcripcion de referencia de la Parte 2: esa la escribes tu escuchando.

Reutiliza el codigo de lectura por partes (HTTP Range) de la Sesion 13, para no
bajar los dos zip completos de ~900 MB cada uno.

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python datos_audio.py

Escribe en  datos/raw/audio/es_peru/  los .wav a 16 kHz mono
y el indice   datos/raw/audio/es_peru/clips.csv
"""
from __future__ import annotations

import csv
import random
import sys
import zipfile
from pathlib import Path

# --- el codigo de descarga vive en la carpeta del curso -----------------------
CURSO = Path(r"C:\Users\Asus\Documents\GitHub\Data-Science-Python")
SESION = CURSO / "sessions" / "13-audio-a-texto"
if not SESION.is_dir():
    sys.exit(f"No encuentro {SESION}. Ajusta la variable CURSO en este archivo.")
sys.path.insert(0, str(SESION))
import datos  # noqa: E402  (trae ZipRemoto, _guardar_16k y OPENSLR73)

# --- parametros ---------------------------------------------------------------
SEMILLA = 2026          # distinta de la 7 que usa la clase: clips diferentes
POR_SEXO = 200          # 400 clips en total, ~6 s cada uno -> unos 40 minutos
MIN_PAL, MAX_PAL = 6, 20
DESTINO = Path("datos/raw/audio/es_peru")


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    indice = DESTINO / "clips.csv"
    filas = []

    for sexo in ["female", "male"]:
        print(f"\nAbriendo el zip de {sexo} por partes...")
        z = zipfile.ZipFile(datos.ZipRemoto(datos.OPENSLR73.format(sexo=sexo)))
        lineas = z.read("line_index.tsv").decode("utf-8").strip().splitlines()
        tabla = [l.split("\t") for l in lineas]
        tabla = [(i, t.strip()) for i, t in tabla if MIN_PAL <= len(t.split()) <= MAX_PAL]
        rng = random.Random(SEMILLA)
        rng.shuffle(tabla)

        n = 0
        for ident, texto in tabla:
            if n >= POR_SEXO:
                break
            ruta = DESTINO / f"{ident}.wav"
            try:
                if not ruta.exists():
                    datos._guardar_16k(z.read(f"{ident}.wav"), ruta)
            except KeyError:
                continue                      # el id del indice no esta en el zip
            hablante = ident.rsplit("_", 1)[0]
            filas.append({
                "archivo": ruta.name,
                "hablante": hablante,
                "sexo": "mujer" if sexo == "female" else "hombre",
                "texto_openslr": texto,       # transcripcion oficial, NO es tu referencia
            })
            n += 1
            if n % 25 == 0:
                print(f"  {n}/{POR_SEXO} clips")
        print(f"  {n} clips de {sexo}")

    with indice.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "hablante", "sexo", "texto_openslr"])
        w.writeheader()
        w.writerows(filas)

    import soundfile as sf
    total = sum(sf.info(DESTINO / r["archivo"]).duration for r in filas)
    hablantes = len({r["hablante"] for r in filas})
    print(f"\n{len(filas)} clips · {hablantes} hablantes · {total/60:.1f} minutos")
    print(f"Carpeta: {DESTINO.resolve()}")
    print(f"Indice:  {indice}")
    if total < 30 * 60:
        print(f"\nAVISO: faltan {30 - total/60:.0f} min para el minimo de 30.")
        print("Sube POR_SEXO en este archivo y vuelve a correrlo.")
    print("\nRecuerda: aun necesitas 1 audio con 2 o mas hablantes para la diarizacion.")


if __name__ == "__main__":
    main()
