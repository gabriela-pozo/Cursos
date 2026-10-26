"""Transcripcion de los clips de espanol peruano (OpenSLR 73). Genera datos/transcripciones.csv.

Linea base del enunciado: faster-whisper `small` en CPU, con VAD siempre activado.
Usa el Transcriptor de voz.py (Sesion 13). Ojo: en voz.py la clave "faster-whisper"
carga large-v3-turbo; aqui se cambia solo el repositorio por el de `small`, sin
tocar el archivo del curso.

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python transcribir_audio.py              # todos los clips
        python transcribir_audio.py --limite 5   # prueba con 5 clips

Se puede cortar y volver a lanzar: salta los clips que ya estan en el CSV de tiempos.

Escribe:
    datos/transcripciones.csv   una fila por clip (columnas exactas del enunciado)
    datos/asr_tiempos.csv       segundos de computo por clip -> factor de tiempo real
    datos/transcripcion.log     registro del avance
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from pathlib import Path

# --- el codigo de voz vive en la carpeta del curso -----------------------------
CURSO = Path(r"C:\Users\Asus\Documents\GitHub\Data-Science-Python")
SESION = CURSO / "sessions" / "13-audio-a-texto"
if not SESION.is_dir():
    sys.exit(f"No encuentro {SESION}. Ajusta la variable CURSO en este archivo.")
sys.path.insert(0, str(SESION))
import voz  # noqa: E402

# --- parametros ------------------------------------------------------------------
REPO_MODELO = "Systran/faster-whisper-small"
MODELO_ASR = "faster-whisper small (CTranslate2 int8, CPU, VAD Silero)"
IDIOMA = "es"
CARPETA = Path("datos/raw/audio/es_peru")
SALIDA = Path("datos/transcripciones.csv")
TIEMPOS = Path("datos/asr_tiempos.csv")
LOG = Path("datos/transcripcion.log")

COLUMNAS = ["id", "archivo_audio", "duracion_seg", "idioma", "texto_asr",
            "modelo_asr", "n_hablantes", "texto_referencia"]
COLUMNAS_TIEMPOS = ["id", "archivo_audio", "duracion_seg", "segundos_computo", "rtf", "modelo_asr"]


def id_estable(ruta: Path) -> str:
    # depende del nombre del archivo, no del orden: agregar clips no cambia los ids
    return f"aud_{re.sub(r'[^A-Za-z0-9]+', '_', ruta.stem).strip('_')}"


def leer_csv(ruta: Path) -> dict[str, dict]:
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def escribir_csv(ruta: Path, columnas: list[str], filas: dict[str, dict]):
    # se escribe a un temporal y se renombra: si el proceso muere, el CSV no queda a medias
    tmp = ruta.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas[k] for k in sorted(filas))
    # en Windows falla si otro programa (Excel, un notebook) tiene el CSV abierto: reintentar
    for intento in range(30):
        try:
            tmp.replace(ruta)
            return
        except PermissionError:
            time.sleep(1)
    raise PermissionError(f"No pude reemplazar {ruta}: esta abierto en otro programa")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, default=None, help="transcribir solo N clips (prueba)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
                        handlers=[logging.FileHandler(LOG, encoding="utf-8"), logging.StreamHandler()])
    for ruidoso in ("httpx", "huggingface_hub", "faster_whisper"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    log = logging.info

    clips = sorted(CARPETA.glob("*.wav"))
    if args.limite:
        clips = clips[:args.limite]

    filas = leer_csv(SALIDA)
    tiempos = leer_csv(TIEMPOS)
    pendientes = [c for c in clips if id_estable(c) not in tiempos]
    log(f"{len(clips)} clips, {len(clips) - len(pendientes)} ya hechos, {len(pendientes)} pendientes")
    if not pendientes:
        return

    voz.MODELOS["faster-whisper"] = voz.MODELOS["faster-whisper"] | {
        "nombre": "faster-whisper small", "hf": REPO_MODELO}
    t = voz.Transcriptor("faster-whisper", device="cpu")
    log(f"Modelo {REPO_MODELO} cargado en {t.segundos_carga:.1f} s")

    t_lote = time.perf_counter()
    audio_total = computo_total = 0.0
    for i, ruta in enumerate(pendientes, start=1):
        ident = id_estable(ruta)
        try:
            audio = voz.cargar_audio(ruta)
            duracion = len(audio) / voz.SR
            t0 = time.perf_counter()
            segs = t.segmentos(audio, idioma=IDIOMA)   # VAD activado dentro de segmentos()
            segundos = time.perf_counter() - t0
        except Exception as e:                          # un clip malo no corta el lote
            log(f"[{i:3d}/{len(pendientes)}] {ruta.name}: ERROR {type(e).__name__}: {e}")
            continue
        texto = " ".join(s.texto for s in segs).strip()

        filas[ident] = {
            "id": ident,
            "archivo_audio": ruta.name,
            "duracion_seg": round(duracion, 2),
            "idioma": IDIOMA,
            "texto_asr": texto,
            "modelo_asr": MODELO_ASR,
            "n_hablantes": 1,   # OpenSLR 73: un solo hablante por clip
            # se conserva la referencia escrita a mano si el clip ya estaba en el CSV
            "texto_referencia": filas.get(ident, {}).get("texto_referencia", ""),
        }
        tiempos[ident] = {
            "id": ident, "archivo_audio": ruta.name, "duracion_seg": round(duracion, 2),
            "segundos_computo": round(segundos, 3), "rtf": round(segundos / duracion, 4),
            "modelo_asr": MODELO_ASR,
        }
        escribir_csv(SALIDA, COLUMNAS, filas)
        escribir_csv(TIEMPOS, COLUMNAS_TIEMPOS, tiempos)

        audio_total += duracion
        computo_total += segundos
        aviso = "  SIN TEXTO (posible clip sin voz)" if not texto else ""
        log(f"[{i:3d}/{len(pendientes)}] {ruta.name}  {duracion:5.1f}s audio  {segundos:5.2f}s computo  "
            f"RTF {segundos / duracion:.3f}  | {texto[:60]}{aviso}")

    if audio_total:
        log(f"Fin: {audio_total / 60:.1f} min de audio en {(time.perf_counter() - t_lote) / 60:.1f} min. "
            f"RTF medio {computo_total / audio_total:.3f}")
    log(f"-> {SALIDA} ({len(filas)} filas) y {TIEMPOS}")


if __name__ == "__main__":
    main()
