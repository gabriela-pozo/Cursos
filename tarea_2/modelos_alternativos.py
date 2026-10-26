"""Modelos alternativos de la Parte 2: Parakeet (ASR) y PaddleOCR-VL (OCR), sobre la muestra fija.

- Parakeet TDT 0.6B v3 sobre los 10 clips de datos/muestra_evaluacion.csv.
- PaddleOCR-VL sobre una submuestra de 4 documentos (en CPU cuesta decenas de segundos por pagina;
  ver 02_evaluacion.ipynb, seccion 12).

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python modelos_alternativos.py

Se puede cortar y volver a lanzar: salta lo que ya esta en los CSV.

Escribe:
    datos/asr_alternativo.csv   id, modelo_asr, texto_asr, duracion_seg, segundos_computo, rtf
    datos/ocr_alternativo.csv   id, modelo_ocr, texto_ocr, segundos_computo
    datos/parametros_ocr.csv    millones de parametros de cada OCR (para comparar tamanos)
"""
from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path

import pandas as pd
import torch

sys.path.insert(0, r"C:\Users\Asus\Documents\GitHub\Data-Science-Python\sessions\13-audio-a-texto")
import voz  # noqa: E402

MUESTRA = pd.read_csv("datos/muestra_evaluacion.csv")
DOCS_VL = [                                  # submuestra: un caso de interes cada uno
    "imp_Memoria_BCRP_1923_p003",            # impreso limpio, con montos
    "man_Manuscrito_cuaderno3",              # manuscrito con cifras y porcentajes
    "fot_Foto_boletas",                      # documento con cifras (boleta)
    "fot_Foto_sintesis_reporte_marzo_2019",  # pagina a dos columnas
]
CARPETA_TIPO = {"impreso": "paginas", "foto": "fotos", "manuscrito": "manuscritos"}
MAX_TOKENS_VL = 2048                         # las paginas de la muestra tienen hasta ~3700 caracteres
SALIDA_ASR = Path("datos/asr_alternativo.csv")
SALIDA_OCR = Path("datos/ocr_alternativo.csv")
SALIDA_PARAM = Path("datos/parametros_ocr.csv")


def hechos(ruta):
    return set(pd.read_csv(ruta)["id"]) if ruta.exists() else set()


def anexar(ruta, fila):
    nuevo = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)


def millones_de_parametros(obj, _prof=0, _vistos=None):
    """Suma los parametros de las redes de PyTorch que hay dentro de un modelo de PaddleOCR
    (misma busqueda que la funcion redes() de la sesion 10)."""
    _vistos = set() if _vistos is None else _vistos
    if id(obj) in _vistos or _prof > 7:
        return 0.0
    _vistos.add(id(obj))
    if isinstance(obj, torch.nn.Module):
        return sum(p.numel() for p in obj.parameters()) / 1e6
    total = 0.0
    for hijo in (vars(obj).values() if hasattr(obj, "__dict__") else []):
        for x in (hijo.values() if isinstance(hijo, dict) else [hijo]):
            if not isinstance(x, (str, int, float, bool, type(None), list, tuple, set)):
                total += millones_de_parametros(x, _prof + 1, _vistos)
    return total


def correr_parakeet():
    clips = MUESTRA[MUESTRA["modalidad"] == "audio"]
    pendientes = clips[~clips["id"].isin(hechos(SALIDA_ASR))]
    if pendientes.empty:
        return
    t = voz.Transcriptor("parakeet-v3", device="cpu")
    nombre = f"{voz.MODELOS['parakeet-v3']['nombre']} (transformers, CPU, float32)"
    t.transcribir(voz.cargar_audio(f"datos/raw/audio/es_peru/{pendientes['archivo'].iloc[0]}"))  # calentamiento
    for r in pendientes.itertuples():
        audio = voz.cargar_audio(f"datos/raw/audio/es_peru/{r.archivo}")
        t0 = time.perf_counter()
        texto = t.transcribir(audio)
        s = time.perf_counter() - t0
        dur = len(audio) / voz.SR
        anexar(SALIDA_ASR, {"id": r.id, "modelo_asr": nombre, "texto_asr": texto, "duracion_seg": round(dur, 2),
                            "segundos_computo": round(s, 3), "rtf": round(s / dur, 4)})
        print(f"[parakeet] {r.id}: rtf {s / dur:.3f} | {texto}", flush=True)
    del t


def correr_paddleocr_vl():
    from paddleocr import PaddleOCR, PaddleOCRVL
    if not SALIDA_PARAM.exists():
        base = PaddleOCR(engine="transformers", use_doc_orientation_classify=True,
                         use_doc_unwarping=False, use_textline_orientation=False)
        anexar(SALIDA_PARAM, {"modelo": "PP-OCRv6 (con clasificador de orientacion)",
                              "millones_parametros": round(millones_de_parametros(base), 1)})
        del base
    pendientes = [i for i in DOCS_VL if i not in hechos(SALIDA_OCR)]
    if not pendientes:
        return
    # orientacion desactivada, como en la sesion 10: las 4 imagenes estan derechas
    vlm = PaddleOCRVL(engine="transformers", use_doc_orientation_classify=False, use_doc_unwarping=False)
    if "PaddleOCR-VL" not in set(pd.read_csv(SALIDA_PARAM)["modelo"]):
        anexar(SALIDA_PARAM, {"modelo": "PaddleOCR-VL", "millones_parametros": round(millones_de_parametros(vlm), 1)})
    filas = MUESTRA.set_index("id")
    for ident in pendientes:
        ruta = Path("datos/raw/documentos") / CARPETA_TIPO[filas.loc[ident, "tipo"]] / filas.loc[ident, "archivo"]
        t0 = time.perf_counter()
        r = vlm.predict(str(ruta), max_new_tokens=MAX_TOKENS_VL)[0]
        s = time.perf_counter() - t0
        texto = r.markdown["markdown_texts"]                 # el modelo responde en Markdown
        texto = re.sub(r"<[^>]+>", " ", texto)               # sin etiquetas HTML (imagenes, tablas)
        texto = re.sub(r"^#+\s*", "", texto, flags=re.M)     # sin marcas de titulo
        anexar(SALIDA_OCR, {"id": ident, "modelo_ocr": f"PaddleOCR-VL (transformers, CPU, max_new_tokens={MAX_TOKENS_VL})",
                            "texto_ocr": " ".join(texto.split()), "segundos_computo": round(s, 1)})
        print(f"[paddleocr-vl] {ident}: {s:.0f} s, {len(texto)} caracteres", flush=True)


if __name__ == "__main__":
    correr_parakeet()
    correr_paddleocr_vl()
