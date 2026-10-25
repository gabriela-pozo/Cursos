"""Extrae las paginas de los PDF escaneados como imagenes para pasarles OCR.

Uso (desde la carpeta tarea_2):

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python extraer_paginas.py

Lee los PDF de  datos/raw/documentos/
Escribe las imagenes en  datos/raw/documentos/paginas/
y un manifiesto en  datos/paginas_manifiesto.csv

El manifiesto dice, por cada pagina, de que PDF viene y si el PDF traia capa
de texto. Eso importa: un PDF sin capa de texto es un escaneo puro, y es el
caso en el que el OCR hace falta de verdad.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

DPI = 300                      # 300 ppp es lo habitual para OCR
ENTRADA = Path("datos/raw/documentos")
SALIDA = ENTRADA / "paginas"
MANIFIESTO = Path("datos/paginas_manifiesto.csv")


# ---------------------------------------------------------------- motor de PDF
def cargar_motor():
    """Devuelve (nombre, modulo). Prueba tres librerias, de mejor a peor."""
    try:
        import pymupdf                                     # noqa: F401
        return "pymupdf", pymupdf
    except ImportError:
        pass
    try:
        import fitz                                        # PyMuPDF antiguo
        return "pymupdf", fitz
    except ImportError:
        pass
    try:
        import pypdfium2                                   # noqa: F401
        return "pypdfium2", pypdfium2
    except ImportError:
        pass
    sys.exit(
        "Falta una libreria para leer PDF.\n"
        "Instala una de estas, dentro de la carpeta del curso:\n"
        "    uv pip install pymupdf\n"
        "    uv pip install pypdfium2"
    )


def paginas_y_texto(motor, mod, ruta: Path):
    """(numero de paginas, caracteres de texto extraible) de un PDF."""
    if motor == "pymupdf":
        with mod.open(ruta) as doc:
            n = doc.page_count
            texto = "".join(p.get_text() for p in doc)
        return n, len(texto.strip())
    doc = mod.PdfDocument(str(ruta))
    n = len(doc)
    texto = ""
    for i in range(n):
        texto += doc[i].get_textpage().get_text_range()
    doc.close()
    return n, len(texto.strip())


def render(motor, mod, ruta: Path, pagina: int, destino: Path):
    """Guarda una pagina (1-indexada) como JPG a DPI puntos por pulgada."""
    if motor == "pymupdf":
        with mod.open(ruta) as doc:
            pix = doc[pagina - 1].get_pixmap(dpi=DPI)
            pix.save(destino)
        return
    doc = mod.PdfDocument(str(ruta))
    img = doc[pagina - 1].render(scale=DPI / 72).to_pil()
    img.convert("RGB").save(destino, quality=92)
    doc.close()


# ---------------------------------------------------------------------- script
def main():
    if not ENTRADA.is_dir():
        sys.exit(f"No existe la carpeta {ENTRADA.resolve()}")
    # en Windows glob no distingue mayusculas: "*.pdf" y "*.PDF" darian cada PDF dos veces
    pdfs = sorted(p for p in ENTRADA.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        sys.exit(f"No hay PDF en {ENTRADA.resolve()}")

    motor, mod = cargar_motor()
    SALIDA.mkdir(parents=True, exist_ok=True)
    MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
    print(f"Motor: {motor} · {len(pdfs)} PDF · {DPI} ppp\n")

    filas = []
    for pdf in pdfs:
        etiqueta = pdf.stem.replace(" ", "_")
        n, chars = paginas_y_texto(motor, mod, pdf)
        tipo = "escaneo puro" if chars == 0 else "escaneo con capa OCR previa"
        print(f"{pdf.name}: {n} paginas · {chars} caracteres de texto · {tipo}")
        for p in range(1, n + 1):
            destino = SALIDA / f"{etiqueta}_p{p:03d}.jpg"
            if not destino.exists():
                render(motor, mod, pdf, p, destino)
            filas.append({
                "archivo": destino.name,
                "pdf_origen": pdf.name,
                "pagina": p,
                "paginas_del_pdf": n,
                "capa_de_texto": "no" if chars == 0 else "si",
                "tipo": tipo,
            })

    with MANIFIESTO.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    puras = sum(1 for r in filas if r["capa_de_texto"] == "no")
    print(f"\n{len(filas)} paginas en {SALIDA}")
    print(f"  {puras} de escaneo puro (sin capa de texto)")
    print(f"  {len(filas) - puras} con capa OCR previa")
    print(f"Manifiesto: {MANIFIESTO}")


if __name__ == "__main__":
    main()
