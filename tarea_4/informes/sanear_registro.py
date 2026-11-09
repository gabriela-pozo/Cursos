"""Oculta datos personales y posibles credenciales de un registro de ejecución de Claude Code (.jsonl).

    uv run informes/sanear_registro.py <registro_crudo.jsonl> <registro_saneado.jsonl>

Lee el registro línea a línea (cada línea es un evento JSON), reemplaza en todos los textos:
  - rutas de la carpeta personal (C:\\Users\\<usuario>, C:/Users/<usuario>, /c/Users/<usuario>, C--Users-<usuario>),
  - correos electrónicos,
  - patrones típicos de claves y tokens (sk-..., ghp_..., xox?-..., Bearer ..., claves API/secret/password con valor),
y luego VUELVE A REVISAR el resultado: si queda algún patrón, termina con error y no guarda el archivo.
Imprime cuántos reemplazos hizo de cada tipo. No altera cifras ni resultados de las herramientas.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

PATRONES = [   # (nombre, expresión, reemplazo); el orden importa: primero lo más específico
    ("ruta_proyecto", re.compile(r"(?:[A-Za-z]:|/[a-z])?[\\/]+Users[\\/]+[^\\/\"\s]+[\\/]+Documents[\\/]+GitHub[\\/]+Cursos[\\/]+tarea_4", re.I), "<PROYECTO>"),
    ("ruta_personal", re.compile(r"(?:[A-Za-z]:|/[a-z])?[\\/]+Users[\\/]+[^\\/\"\s]+", re.I), "<HOME>"),
    ("ruta_claude_codificada", re.compile(r"[A-Za-z]--Users-[^\\/\"\s]+?(?=-Documents|-AppData|[\\/\"\s]|$)", re.I), "<HOME-CODIFICADO>"),
    ("correo", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<CORREO>"),
    ("clave_sk", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "<CLAVE>"),
    ("token_github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "<TOKEN>"),
    ("token_slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "<TOKEN>"),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.I), "Bearer <TOKEN>"),
    ("clave_asignada", re.compile(r"(?i)\b(api[_-]?key|secret|passw(?:or)?d|token)\b(\"?\s*[:=]\s*\"?)[^\s\"',;]{6,}"), r"\1\2<OCULTO>"),
    ("usuario_suelto", re.compile(r"\bAsus\b"), "<USUARIO>"),
]
# lo que NO debe quedar tras sanear (revisión final)
RESIDUOS = [re.compile(p) for p in (r"Users[\\/]+(?!<)", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", r"\bsk-[A-Za-z0-9_-]{16,}",
                                      r"\bgh[pousr]_[A-Za-z0-9]{20,}", r"\bxox[abprs]-", r"\bAsus\b")]


def sanear_texto(texto: str, cuenta: Counter) -> str:
    for nombre, patron, reemplazo in PATRONES:
        texto, n = patron.subn(reemplazo, texto)
        cuenta[nombre] += n
    return texto


def sanear(valor, cuenta: Counter):
    if isinstance(valor, str):
        return sanear_texto(valor, cuenta)
    if isinstance(valor, list):
        return [sanear(v, cuenta) for v in valor]
    if isinstance(valor, dict):
        return {sanear_texto(k, cuenta) if isinstance(k, str) else k: sanear(v, cuenta) for k, v in valor.items()}
    return valor


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    cuenta, lineas = Counter(), []
    for n, linea in enumerate(entrada.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            lineas.append(json.dumps(sanear(json.loads(linea), cuenta), ensure_ascii=False))
        except json.JSONDecodeError:
            raise SystemExit(f"ERROR: la línea {n} no es JSON válido; no se guardó nada.")
    texto = "\n".join(lineas) + "\n"
    for r in RESIDUOS:
        m = r.search(texto)
        if m:
            raise SystemExit(f"ERROR: tras sanear sigue apareciendo un dato sensible ({r.pattern!r} cerca de "
                             f"{texto[max(0, m.start() - 30):m.end() + 30]!r}). No se guardó el archivo.")
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    print(f"Saneado: {len(lineas)} eventos -> {salida}")
    for nombre, _, _ in PATRONES:
        print(f"  {nombre}: {cuenta[nombre]} reemplazo(s)")


if __name__ == "__main__":
    main()
