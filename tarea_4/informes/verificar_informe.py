"""Verifica que CADA número de informes/informe_final.md aparezca en informes/trazabilidad.md. Falla si hay uno que no.

    uv run informes/verificar_informe.py [informe.md] [trazabilidad.md]

Así ninguna cifra del informe puede haberse escrito a mano o de memoria: todas deben estar en la tabla de trazabilidad,
que genera informes/generar_trazabilidad.py desde los resultados de las herramientas.

Qué se revisa y qué se ignora (todo escrito aquí para que sea auditable):
  - Se revisan los números del texto: enteros, decimales ("8.81"), miles ("108,664") y períodos ("2020-01", "2024-12").
  - Se ignoran los números que no son cifras: dentro de bloques de código y `código en línea`, destinos de enlaces e
    imágenes, nombres alfanuméricos (PN01273PM, personas_2024.parquet), numeración de listas ("1."), numeración de
    secciones ("## 3. Resultados") y rótulos «Hallazgo N», «Figura N», «Tabla N».
  - Un número del informe es válido si aparece EXACTAMENTE igual (mismo texto) como número en trazabilidad.md.
También comprueba lo estructural: la pregunta exacta, al menos 3 hallazgos y que las figuras referenciadas existan.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PREGUNTA = ("¿Cómo evolucionó la inflación a 12 meses en Lima entre 2020 y 2024, y qué diferencias territoriales "
            "(urbano/rural y departamental) presentaba la pobreza monetaria en 2024?")
# El signo menos cuenta como parte del número (-0.29): así un negativo no se escapa de la revisión.
NUMERO = re.compile(r"(?<![\w.,/])(?:\d{4}-\d{2}(?:-\d{2})?|-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)(?![\w])")


def sin_ruido(texto: str) -> str:
    """Quita lo que contiene números que no son cifras (ver la lista en la cabecera)."""
    texto = re.sub(r"```.*?```", " ", texto, flags=re.S)                  # bloques de código
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)                 # comentarios HTML
    texto = re.sub(r"`[^`\n]*`", " ", texto)                              # código en línea
    texto = re.sub(r"\]\([^)]*\)", "]", texto)                            # destinos de enlaces e imágenes
    texto = re.sub(r"https?://\S+", " ", texto)                           # URLs sueltas
    texto = re.sub(r"\b\d{1,2}-(?:ene|feb|mar|abr|may|jun|jul|ago|set|sep|oct|nov|dic)[a-z]*-\d{4}\b", " ", texto, flags=re.I)   # fechas «8-nov-2026»
    texto = re.sub(r"(?m)^\s*(?:#+\s*)?\d+[.)]\s+", "", texto)            # numeración de listas y de secciones
    texto = re.sub(r"\b(?:Hallazgo|Figura|Tabla|Paso)\s+\d+", " ", texto)  # rótulos
    return texto


def numeros(texto: str) -> list[str]:
    return NUMERO.findall(sin_ruido(texto))


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):   # acentos correctos también en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    informe = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "informes" / "informe_final.md"
    traza = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "informes" / "trazabilidad.md"
    for p in (informe, traza):
        if not p.exists():
            raise SystemExit(f"ERROR: falta {p}.")
    texto, autorizados = informe.read_text(encoding="utf-8"), set(numeros(traza.read_text(encoding="utf-8")))
    problemas = []

    # 1) cada número, con la línea donde está
    revisados, ausentes = 0, []
    for n, linea in enumerate(texto.splitlines(), 1):
        for num in numeros(linea):
            revisados += 1
            if num not in autorizados:
                ausentes.append((n, num, linea.strip()[:110]))
    if ausentes:
        problemas.append(f"{len(ausentes)} número(s) del informe NO están en {traza.name}:")
        problemas += [f"    línea {n}: «{num}»  ->  {ctx}" for n, num, ctx in ausentes]

    # 2) estructura mínima exigida por la tarea
    if PREGUNTA not in texto:
        problemas.append("La pregunta de investigación no aparece escrita exactamente como se acordó.")
    hallazgos = len(re.findall(r"(?m)^#{2,4}\s*Hallazgo\s+\d+", texto))
    if hallazgos < 3:
        problemas.append(f"Se necesitan al menos 3 hallazgos con encabezado «Hallazgo N»; hay {hallazgos}.")
    for destino in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texto):
        if not (informe.parent / destino).resolve().exists():
            problemas.append(f"La imagen referenciada no existe: {destino}")

    if problemas:
        print("VERIFICACIÓN FALLIDA\n" + "\n".join(problemas), file=sys.stderr)
        sys.exit(1)
    print(f"VERIFICACIÓN APROBADA: los {revisados} números del informe están en {traza.name}; "
          f"{hallazgos} hallazgos; pregunta exacta presente; figuras referenciadas existen.")


if __name__ == "__main__":
    main()
