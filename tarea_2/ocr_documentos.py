"""OCR del corpus de documentos con PaddleOCR. Genera datos/documentos.csv.

Estructura de carpetas que espera (dentro de tarea_2):

    datos/raw/documentos/paginas/      <- paginas de PDF (impresos)
    datos/raw/documentos/fotos/        <- fotos con sombra o inclinacion
    datos/raw/documentos/manuscritos/  <- paginas escritas a mano

El 'tipo' de cada documento sale de la carpeta donde esta, asi que basta con
ordenar las imagenes para que el CSV salga bien.

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python ocr_documentos.py

Escribe:
    datos/documentos.csv        una fila por imagen (columnas que pide el issue)
    datos/ocr_lineas.csv        una fila por linea detectada, con su confianza
"""
from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path

import numpy as np

# Modelo y parametros, declarados aqui para poder reportarlos en la metodologia
MODELO_OCR = "PP-OCRv6 (PaddleOCR, engine=transformers)"
OPCIONES = dict(
    use_doc_orientation_classify=True,   # True: endereza paginas giradas 90 grados
    use_doc_unwarping=False,             # no "planchar" hojas dobladas
    use_textline_orientation=False,      # no girar cada linea
)

RAIZ = Path("datos/raw/documentos")
CARPETAS = {                             # carpeta -> valor de la columna 'tipo'
    "paginas": "impreso",
    "fotos": "foto",
    "manuscritos": "manuscrito",
}
EXTENSIONES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SALIDA = Path("datos/documentos.csv")
SALIDA_LINEAS = Path("datos/ocr_lineas.csv")


def imagenes():
    """Lista [(ruta, tipo)] de todas las imagenes del corpus, ordenadas."""
    items = []
    for carpeta, tipo in CARPETAS.items():
        d = RAIZ / carpeta
        if not d.is_dir():
            print(f"  aviso: no existe {d}")
            continue
        encontradas = sorted(p for p in d.iterdir() if p.suffix.lower() in EXTENSIONES)
        print(f"  {carpeta}: {len(encontradas)} imagenes -> tipo '{tipo}'")
        items += [(p, tipo) for p in encontradas]
    return items


def leer(ocr, ruta: Path):
    """OCR de una imagen. Devuelve (texto unido, lista de (texto, confianza))."""
    r = ocr.predict(str(ruta))[0]
    textos = r["rec_texts"]
    scores = [float(s) for s in r["rec_scores"]]
    return " ".join(t.strip() for t in textos if t.strip()), list(zip(textos, scores))


def main():
    pares = []
    print("Buscando imagenes:")
    pares = imagenes()
    if not pares:
        sys.exit(f"\nNo hay imagenes en {RAIZ.resolve()}")
    print(f"\nTotal: {len(pares)} imagenes\n")

    from paddleocr import PaddleOCR
    print("Cargando PaddleOCR (la primera vez descarga los modelos)...")
    t0 = time.perf_counter()
    ocr = PaddleOCR(engine="transformers", **OPCIONES)
    print(f"Listo en {time.perf_counter() - t0:.0f} s\n")

    filas, lineas = [], []
    for i, (ruta, tipo) in enumerate(pares, start=1):
        # id estable: depende del nombre del archivo, no del orden. Asi puedes
        # volver a correr el script tras agregar imagenes sin que cambien los ids
        # de las que ya transcribiste a mano.
        ident = f"{tipo[:3]}_{re.sub(r'[^A-Za-z0-9]+', '_', ruta.stem).strip('_')}"
        t0 = time.perf_counter()
        try:
            texto, detalle = leer(ocr, ruta)
        except Exception as e:                       # una imagen mala no corta el lote
            print(f"[{i:3d}/{len(pares)}] {ruta.name}: ERROR {type(e).__name__}: {e}")
            texto, detalle = "", []
        segundos = time.perf_counter() - t0
        confs = [c for _, c in detalle]
        media = float(np.mean(confs)) if confs else 0.0
        dudosas = sum(1 for c in confs if c < 0.90)
        print(f"[{i:3d}/{len(pares)}] {ruta.name[:46]:46s} {tipo:10s} "
              f"{len(detalle):3d} lineas  conf {media:.2f}  {segundos:5.1f}s")

        filas.append({
            "id": ident,
            "archivo": ruta.name,
            "tipo": tipo,
            "fuente": "",                    # completar con la fila de fuentes.csv
            "texto_ocr": texto,
            "modelo_ocr": MODELO_OCR,
            "texto_referencia": "",          # solo para la muestra de 10 de la Parte 2
        })
        for n, (t, c) in enumerate(detalle, start=1):
            lineas.append({"id": ident, "archivo": ruta.name, "tipo": tipo,
                           "linea": n, "texto": t, "confianza": round(c, 4)})
        del confs, dudosas

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    with SALIDA_LINEAS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "archivo", "tipo", "linea", "texto", "confianza"])
        w.writeheader()
        w.writerows(lineas)

    print(f"\n{len(filas)} documentos -> {SALIDA}")
    print(f"{len(lineas)} lineas con confianza -> {SALIDA_LINEAS}")
    print("\nFalta completar a mano en documentos.csv:")
    print("  - 'fuente': el id correspondiente de fuentes.csv")
    print("  - 'texto_referencia': solo en los 10 que transcribas para la Parte 2")


if __name__ == "__main__":
    main()
