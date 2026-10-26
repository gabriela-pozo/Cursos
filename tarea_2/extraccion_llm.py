"""Extraccion de campos en JSON con un LLM local (Qwen2.5-0.5B-Instruct). Genera datos/extraccion_llm.csv.

Igual que en la sesion 08-llms-rag (llms_a_prueba.ipynb): transformers en CPU, float32 y
decodificacion sin azar (greedy), con la plantilla de chat del modelo.

Entrada: el texto ya seudonimizado de datos/documentos.csv (texto_ocr) y de
datos/transcripciones.csv (texto_asr).

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python extraccion_llm.py              # todo el corpus
        python extraccion_llm.py --limite 5   # prueba con 5 textos

Se puede cortar y volver a lanzar: salta los ids que ya estan en el CSV.

Escribe:
    datos/extraccion_llm.csv          id, modalidad, campos_json, modelo_llm, fecha (columnas del enunciado)
    datos/extraccion_llm_crudo.jsonl  la respuesta tal como la dio el modelo, para auditar
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd

MODELO = "Qwen/Qwen2.5-0.5B-Instruct"
MODELO_LLM = f"{MODELO} (transformers, CPU, float32, greedy)"
MAX_CARACTERES = 3000      # se corta el texto de entrada: el mas largo del corpus pasa de 5000
MAX_TOKENS = 300
PENALIZACION_REINTENTO = 1.15   # solo si la 1.a respuesta no es JSON valido (bucles de repeticion)
SALIDA = Path("datos/extraccion_llm.csv")
CRUDO = Path("datos/extraccion_llm_crudo.jsonl")
COLUMNAS = ["id", "modalidad", "campos_json", "modelo_llm", "fecha"]

# esquema cerrado: los 3 obligatorios y los opcionales que valen null si no aparecen
OBLIGATORIOS = ["modalidad", "tema", "resumen"]
OPCIONALES = ["fecha", "lugar", "organizaciones", "cifras"]
CAMPOS = OBLIGATORIOS + OPCIONALES

SISTEMA = """Eres un asistente que extrae informacion de textos en espanol y responde SOLO con un objeto JSON valido, sin texto antes ni despues.

El texto puede venir de un OCR o de una transcripcion de audio, y puede tener errores de lectura.

Devuelve exactamente estas claves y ninguna otra:
- "modalidad": copia el valor que se indica ("documento" o "audio").
- "tema": el tema principal en pocas palabras.
- "resumen": una oracion que resuma el texto.
- "fecha": una fecha que aparezca escrita en el texto, copiada tal cual. Si no hay, null.
- "lugar": un lugar que aparezca escrito en el texto. Si no hay, null.
- "organizaciones": lista de instituciones o empresas nombradas en el texto. Si no hay, null.
- "cifras": lista de hasta 5 montos, porcentajes o cantidades que aparezcan en el texto, copiados tal cual. Si no hay, null.

Reglas:
- Usa null cuando el dato no aparece en el texto. No adivines ni inventes datos.
- No agregues claves que no esten en la lista.
- Si el texto es ilegible, pon "tema": null y "resumen": null."""

USUARIO = """Modalidad: {modalidad}

Texto:
\"\"\"
{texto}
\"\"\""""


def textos() -> pd.DataFrame:
    docs = pd.read_csv("datos/documentos.csv", dtype=str, keep_default_na=False)
    aud = pd.read_csv("datos/transcripciones.csv", dtype=str, keep_default_na=False)
    return pd.concat([
        pd.DataFrame({"id": docs["id"], "modalidad": "documento", "texto": docs["texto_ocr"]}),
        pd.DataFrame({"id": aud["id"], "modalidad": "audio", "texto": aud["texto_asr"]}),
    ], ignore_index=True)


def normalizar(x: str) -> str:
    x = unicodedata.normalize("NFKD", str(x).lower())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", x).strip()


def literal(valor, texto_norm: str) -> bool:
    return normalizar(valor) in texto_norm


def parsear(respuesta: str, modalidad: str, texto: str) -> tuple[dict, list[str]]:
    """Del texto del modelo saca el JSON y lo ajusta al esquema. Devuelve (campos, avisos).

    Regla de no inventar: fecha, lugar, organizaciones y cifras deben aparecer escritos en el
    texto de entrada (sin importar mayusculas, tildes ni espacios). Lo que no aparece pasa a null.
    tema y resumen son redaccion del modelo y no se pueden comprobar asi: se auditan a mano.
    """
    avisos = []
    m = re.search(r"\{.*\}", respuesta, flags=re.S)       # el modelo a veces lo envuelve en ```json
    try:
        crudo = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        crudo = None
    if not isinstance(crudo, dict):
        return {c: None for c in CAMPOS} | {"modalidad": modalidad}, ["json_invalido"]
    extra = sorted(set(crudo) - set(CAMPOS))
    if extra:
        avisos.append("claves_extra_descartadas:" + ",".join(extra))
    campos = {c: crudo.get(c) for c in CAMPOS}
    for c, v in campos.items():                            # "", [], "null" -> null
        if v in ("", [], {}) or (isinstance(v, str) and v.strip().lower() in {"null", "none", "n/a"}):
            campos[c] = None
    texto_norm = normalizar(texto)
    for c in OPCIONALES:
        v = campos[c]
        if isinstance(v, list):
            dados = [x for x in v if x is not None]
            buenos = [x for x in dados if literal(x, texto_norm)]
            if len(buenos) < len(dados):
                avisos.append(f"{c}:{len(dados) - len(buenos)}_no_aparecen")
            campos[c] = buenos or None
        elif v is not None and not literal(v, texto_norm):
            avisos.append(f"{c}:no_aparece")
            campos[c] = None
    if campos["modalidad"] != modalidad:                   # la modalidad la sabemos: no se deja al modelo
        avisos.append(f"modalidad_corregida:{campos['modalidad']}")
        campos["modalidad"] = modalidad
    return campos, avisos


def generar(tok, llm, entrada, **opciones) -> str:
    import torch
    with torch.no_grad():
        salida = llm.generate(**entrada, max_new_tokens=MAX_TOKENS, do_sample=False, **opciones)
    return tok.decode(salida[0, entrada["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, default=None)
    args = p.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(MODELO)
    llm = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.float32).eval()

    hechos = set(pd.read_csv(SALIDA)["id"]) if SALIDA.exists() else set()
    pendientes = textos()
    pendientes = pendientes[~pendientes["id"].isin(hechos)]
    if args.limite:
        pendientes = pendientes.head(args.limite)
    print(f"{len(hechos)} ya hechos, {len(pendientes)} pendientes")

    nuevo = not SALIDA.exists()
    with SALIDA.open("a", newline="", encoding="utf-8") as f_csv, CRUDO.open("a", encoding="utf-8") as f_crudo:
        w = csv.DictWriter(f_csv, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        for i, r in enumerate(pendientes.itertuples(), start=1):
            msgs = [{"role": "system", "content": SISTEMA},
                    {"role": "user", "content": USUARIO.format(modalidad=r.modalidad,
                                                               texto=r.texto[:MAX_CARACTERES])}]
            entrada = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                              return_tensors="pt", return_dict=True)
            texto = r.texto[:MAX_CARACTERES]
            t0 = time.perf_counter()
            respuesta = generar(tok, llm, entrada)
            campos, avisos = parsear(respuesta, r.modalidad, texto)
            if "json_invalido" in avisos:
                respuesta = generar(tok, llm, entrada, repetition_penalty=PENALIZACION_REINTENTO)
                campos, avisos = parsear(respuesta, r.modalidad, texto)
                avisos.insert(0, "reintento")
            segundos = time.perf_counter() - t0

            w.writerow({"id": r.id, "modalidad": r.modalidad,
                        "campos_json": json.dumps(campos, ensure_ascii=False),
                        "modelo_llm": MODELO_LLM,
                        "fecha": datetime.datetime.now().isoformat(timespec="seconds")})
            f_crudo.write(json.dumps({"id": r.id, "respuesta": respuesta, "avisos": avisos,
                                      "tokens_entrada": int(entrada["input_ids"].shape[1]),
                                      "segundos": round(segundos, 2)}, ensure_ascii=False) + "\n")
            f_csv.flush()
            f_crudo.flush()
            print(f"[{i}/{len(pendientes)}] {r.id[:50]:50s} {segundos:5.1f}s {' '.join(avisos)}", flush=True)


if __name__ == "__main__":
    main()
