"""Evaluación de la Tarea 4: ¿mejoran las respuestas con el MCP BCRP y las Skills ENAHO?

    uv run evaluacion/evaluar.py --modos A B --ids 4          # prueba: una pregunta por modo
    uv run evaluacion/evaluar.py --modos A B                  # las 20 ejecuciones (pedir OK antes)

Lógica copiada de sessions/04-mcp-claude-code/proyecto/evaluar.py (el original no se toca): cada pregunta va a
`claude -p` en una sesión independiente (--no-session-persistence), pide una respuesta estructurada (JSON schema) y
la califica un script contra evaluacion/preguntas.csv. Cambios respecto al original, todos a propósito:
  - dos modos, A (sin nada) y B (con MCP + Skills), documentados abajo;
  - preguntas con varias cifras y con etiqueta (mes, departamento); las esperadas y tolerancias se LEEN del CSV;
  - registro completo en stream-json (herramientas usadas, errores), saneado de rutas personales antes de guardarse;
  - ejecución secuencial (los tiempos no se contaminan entre sí).

MODO A — desde una carpeta temporal VACÍA fuera del repo (tempfile). Herramientas habilitadas: NINGUNA.
  --tools ""               sin Bash, Read, Skill, WebSearch ni ninguna otra herramienta integrada
  --strict-mcp-config      sin servidores MCP (no se pasa ningún --mcp-config)
  --disable-slash-commands sin skills ni comandos
  --setting-sources project solo ajustes del proyecto (la carpeta está vacía), así no entran plugins ni ajustes de usuario
  Es decir: Claude responde de memoria; ve sin .mcp.json, skills, datos ni salidas.
MODO B — desde tarea_4/, con .mcp.json (servidor bcrp) y .claude/skills. Herramientas habilitadas:
  --setting-sources project,local: solo las skills y ajustes de ESTE proyecto (sin los plugins del usuario).
  OJO: la ejecución de la Parte 3 (informes/, evidencias_ia/integracion/) se hizo ANTES de este cambio, con los plugins
  del usuario cargados; la evaluación sí usa --setting-sources project,local. Modelo: sonnet en ambos modos.
  Skill, Read, Bash (solo `uv run`), ReadMcpResourceTool y todas las del servidor mcp__bcrp. Igual que en la Parte 3.
  Antes de CADA pregunta del modo B se vacía mcp/cache/ (así cada una arranca en frío y el tiempo es comparable).
"""
import argparse
import csv
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EVAL = RAIZ / "evaluacion"
LOGS = RAIZ / "evidencias_ia" / "evaluacion"
CACHE = RAIZ / "mcp" / "cache"

ESQUEMA = {"type": "object", "required": ["valores", "etiqueta", "respuesta", "fuente"],
           "properties": {"valores": {"type": "array", "items": {"type": ["number", "null"]}},
                          "etiqueta": {"type": ["string", "null"]},
                          "respuesta": {"type": "string"}, "fuente": {"type": "string"}}}
INSTRUCCION = (
    "Responde la pregunta y devuelve el JSON pedido. En «valores» pon SOLO números, en el orden en que la pregunta "
    "los pide: porcentajes como número (0.81 para 0.81 %), brechas en puntos porcentuales, tipo de cambio en S/ por "
    "US$, conteos como entero sin separadores. Si la pregunta también pide un mes o un departamento, ponlo en "
    "«etiqueta» (por ejemplo «junio 2020» o «Ica»); si no, null. Si no puedes saber una cifra con certeza, pon null "
    "en su lugar: no estimes. En «respuesta» escribe la respuesta completa en una o dos frases. En «fuente» di "
    "exactamente de dónde sale cada cifra (serie, tabla, archivo o herramienta; o «memoria» si es de memoria).\n\nPregunta: ")
ETIQUETAS = {"4": "junio 2020", "8": "Ica", "10": "Cajamarca"}   # parte textual de la esperada (el resto se lee del CSV)
MESES = {m: f"{i:02d}" for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto setiembre septiembre octubre noviembre diciembre".split(), 1)}
MESES["septiembre"] = "09"
CAUSAL = re.compile(r"\b(caus[oó]|a causa de|debido a|se debe|provoc\w*|gener[aó]\w* pobreza|explic\w+ (?:la|el) pobreza|"
                    r"efecto (?:de|sobre) la inflaci\w+|impact\w+ (?:en|sobre) la pobreza)\b", re.I)

MODOS = {
    "A": {"cwd": None, "args": ["--tools", "", "--strict-mcp-config", "--disable-slash-commands",
                                 "--setting-sources", "project"],
          "herramientas": "ninguna (--tools '' + sin MCP + sin skills); carpeta temporal vacía fuera del repo"},
    "B": {"cwd": RAIZ, "args": ["--mcp-config", ".mcp.json", "--strict-mcp-config",
                                "--tools", "Skill,Read,Bash", "--setting-sources", "project,local",
                                "--allowedTools", "Skill", "Read", "Bash(uv run:*)", "mcp__bcrp", "ReadMcpResourceTool"],
          "herramientas": "Skill, Read, Bash(uv run), ReadMcpResourceTool, mcp__bcrp (5 herramientas del servidor); desde tarea_4/"},
}


def cargar_saneador():
    spec = importlib.util.spec_from_file_location("sanear_registro", RAIZ / "informes" / "sanear_registro.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- calificación (todo por script) ----------
def quitar_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def fichas(texto: str) -> set[str]:
    """«Junio de 2020», «2020-06» y «junio 2020» dan las mismas fichas {06, 2020}."""
    palabras = re.findall(r"[a-z0-9]+", quitar_acentos(texto.lower()))
    return {MESES.get(p, p) for p in palabras}


def esperadas(fila: dict) -> tuple[list[float], list[float], str | None]:
    """Cifras esperadas, tolerancias y etiqueta, leídas de la fila del CSV (no escritas aparte)."""
    etiqueta = ETIQUETAS.get(fila["id"])
    texto = fila["respuesta_esperada"].replace(etiqueta, "") if etiqueta else fila["respuesta_esperada"]
    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", texto)]
    tol = [0.0] if "exacto" in fila["tolerancia"].lower() else [float(x) for x in re.findall(r"\d+\.?\d*", fila["tolerancia"])]
    if len(tol) == 1 and len(nums) > 1:
        tol = tol * len(nums)
    if len(tol) != len(nums):
        raise SystemExit(f"ERROR: la pregunta {fila['id']} tiene {len(nums)} cifras y {len(tol)} tolerancias en el CSV.")
    return nums, tol, etiqueta


def calificar(fila: dict, salida: dict | None) -> tuple[str, str]:
    """-> (resultado, detalle). resultado: acierta | se equivoca | no sabe | sin respuesta."""
    if not salida:
        return "sin respuesta", "no hubo JSON estructurado"
    nums, tol, etiqueta = esperadas(fila)
    vals = salida.get("valores") or []
    if not vals or any(v is None for v in vals[:len(nums)]) or len(vals) < len(nums):
        return "no sabe", f"valores={vals}"
    detalle, ok = [], True
    for i, (e, t) in enumerate(zip(nums, tol)):
        d = abs(float(vals[i]) - e)
        bien = d <= t + 1e-9
        ok &= bien
        detalle.append(f"cifra{i + 1}: {vals[i]} vs {e} (dif {d:.4g}, tol {t}) {'OK' if bien else 'FALLA'}")
    if etiqueta:
        bien = fichas(etiqueta) <= fichas(salida.get("etiqueta") or "")
        ok &= bien
        detalle.append(f"etiqueta: «{salida.get('etiqueta')}» vs «{etiqueta}» {'OK' if bien else 'FALLA'}")
    if fila["tipo"] == "Combinada":   # criterio de la tarea: además, sin sugerir causalidad
        m = CAUSAL.search(salida.get("respuesta", ""))
        if m:
            ok = False
            detalle.append(f"posible causalidad: «{m.group(0)}» (revisar a mano)")
    return ("acierta" if ok else "se equivoca"), "; ".join(detalle)


# ---------- ejecución ----------
def analizar(eventos: list[dict]) -> dict:
    herramientas, errores, final, ids = [], [], {}, {}
    for e in eventos:
        if e.get("type") == "assistant":
            for b in e.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_use" and b["name"] != "StructuredOutput":
                    herramientas.append(b["name"] + (f"({b['input'].get('skill')})" if b["name"] == "Skill" else ""))
                    ids[b["id"]] = b["name"]
        elif e.get("type") == "user":
            for b in (e.get("message", {}).get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                    errores.append(f"{ids.get(b.get('tool_use_id'), '?')}: {str(b.get('content'))[:150]}")
        elif e.get("type") == "result":
            final = e
    return {"herramientas": herramientas, "errores": errores, "final": final}


def ejecutar(fila: dict, modo: str, modelo: str, saneador) -> dict:
    cfg = MODOS[modo]
    temporal = Path(tempfile.mkdtemp(prefix="eval_modoA_")) if modo == "A" else None
    cwd = temporal or cfg["cwd"]
    if modo == "B" and CACHE.exists():   # tiempos justos: cada pregunta del modo B arranca sin caché
        for f in CACHE.iterdir():
            f.unlink() if f.is_file() else shutil.rmtree(f)
    cmd = ["claude", "-p", INSTRUCCION + fila["pregunta"], "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo, *cfg["args"]]
    t = time.time()
    error_proceso = ""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=cwd)
        crudo, stderr = proc.stdout, proc.stderr
        if proc.returncode != 0:
            error_proceso = f"claude terminó con código {proc.returncode}: {stderr[-200:]}"
    except subprocess.TimeoutExpired as ex:
        crudo, stderr, error_proceso = (ex.stdout or ""), "", "tiempo agotado (900 s)"
        crudo = crudo if isinstance(crudo, str) else crudo.decode("utf-8", "ignore")
    segundos = round(time.time() - t, 1)
    if temporal:
        contenido = [p.name for p in temporal.iterdir()]   # constancia: la carpeta seguía vacía
        shutil.rmtree(temporal, ignore_errors=True)
    eventos = []
    for linea in crudo.splitlines():
        try:
            eventos.append(json.loads(linea))
        except json.JSONDecodeError:
            pass
    info = analizar(eventos)
    salida = info["final"].get("structured_output")
    if salida is None and isinstance(info["final"].get("result"), str):   # por si llegó como texto JSON
        try:
            salida = json.loads(info["final"]["result"])
        except json.JSONDecodeError:
            pass
    resultado, detalle = calificar(fila, salida)
    errores = ([error_proceso] if error_proceso else []) + info["errores"]
    if info["final"].get("is_error"):
        errores.append(f"resultado con is_error: {str(info['final'].get('result'))[:150]}")

    # registro completo, saneado (rutas personales -> <HOME>/<PROYECTO>), con cabecera que documenta el modo
    from collections import Counter
    cuenta = Counter()
    cabecera = {"type": "evaluacion_meta", "id": fila["id"], "modo": modo, "modelo": modelo,
                "herramientas_habilitadas": cfg["herramientas"], "cwd": str(cwd), "comando": [c for c in cmd if c != cmd[2]],
                "carpeta_vacia_al_terminar": (not contenido) if temporal else None}
    lineas = [saneador.sanear(x, cuenta) for x in [cabecera, *eventos]]
    texto = "\n".join(json.dumps(x, ensure_ascii=False) for x in lineas) + "\n"
    for r in saneador.RESIDUOS:
        m = r.search(texto)
        if m:
            raise SystemExit(f"ERROR: dato sensible en el registro de la pregunta {fila['id']} modo {modo}: no se guardó.")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"pregunta{int(fila['id']):02d}_modo{modo}.jsonl").write_text(texto, encoding="utf-8")

    return {"id": fila["id"], "tipo": fila["tipo"], "modo": modo, "modelo": modelo,
            "respuesta_esperada": fila["respuesta_esperada"], "tolerancia": fila["tolerancia"],
            "respuesta": (salida or {}).get("respuesta", ""), "valores": json.dumps((salida or {}).get("valores")),
            "etiqueta": (salida or {}).get("etiqueta"), "fuente_citada": (salida or {}).get("fuente", ""),
            "herramientas_usadas": " | ".join(info["herramientas"]) or "ninguna",
            "resultado": resultado, "detalle_calificacion": detalle, "segundos": segundos,
            "turnos": info["final"].get("num_turns"), "costo_usd": info["final"].get("total_cost_usd"),
            "errores": " || ".join(errores)}


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--ids", nargs="+", help="solo estas preguntas (por defecto, las 10)")
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--salida", default=str(EVAL / "resultados.csv"))
    a = p.parse_args()
    with open(EVAL / "preguntas.csv", encoding="utf-8", newline="") as f:
        filas = [r for r in csv.DictReader(f) if not a.ids or r["id"] in a.ids]
    if not filas:
        raise SystemExit("ERROR: ninguna pregunta coincide con --ids.")
    saneador = cargar_saneador()
    resultados = []
    for fila in filas:
        for modo in a.modos:
            print(f"[{modo}] pregunta {fila['id']}: {fila['pregunta'][:70]}...", flush=True)
            r = ejecutar(fila, modo, a.modelo, saneador)
            resultados.append(r)
            print(f"      -> {r['resultado']} | {r['segundos']} s | herramientas: {r['herramientas_usadas']}\n"
                  f"         {r['detalle_calificacion']}", flush=True)
    salida = Path(a.salida)
    with open(salida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(resultados[0]))
        w.writeheader()
        w.writerows(resultados)
    print(f"\nGuardado: {salida}")


if __name__ == "__main__":
    main()
