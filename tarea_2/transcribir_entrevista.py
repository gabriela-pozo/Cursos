"""Entrevista de Espika FM: corta dos tramos, los transcribe con VAD + diarizacion y exporta CSV, SRT y TXT.

Fuente: Espika FM 90.7, "Al mundo le falta un tornillo", 21/11/2020, bloque 4 (CC BY-SA 4.0).
https://archive.org/details/espika-fm-al-mundo-le-falta-un-tornillo-20201121

Dos hablantes: el conductor (uruguayo, NO es espanol peruano) y el entrevistado (peruano).
El tramo con musica se incluye a proposito como caso dificil.

Uso, desde tarea_2:

    uv run --project C:\\Users\\Asus\\Documents\\GitHub\\Data-Science-Python ^
        python transcribir_entrevista.py

Escribe:
    datos/raw/audio/entrevistas/tramos/<id>.wav   los tramos cortados (no se versionan)
    datos/entrevistas/<id>.csv|.srt|.txt          segmentos con hablante, subtitulos y texto
    datos/transcripciones.csv                      agrega o actualiza las filas de los tramos
    datos/asr_tiempos.csv                          segundos de computo de ASR y de diarizacion
"""
from __future__ import annotations

import time
from pathlib import Path

import soundfile as sf

# reutiliza la configuracion de la linea base (modelo, columnas, escritura segura de CSV)
from transcribir_audio import (COLUMNAS, COLUMNAS_TIEMPOS, IDIOMA, MODELO_ASR, REPO_MODELO, SALIDA,
                               TIEMPOS, escribir_csv, leer_csv, voz)

MP3 = Path("datos/raw/audio/entrevistas/"
           "EspikaFM-AlMundo-20201121-4-EntreOidos-PepeArevalo-Peru-Musica-HermanosSantaCruz.mp3")
CARPETA_TRAMOS = Path("datos/raw/audio/entrevistas/tramos")
CARPETA_SALIDA = Path("datos/entrevistas")

# inicio y fin en segundos del mp3. Elegidos con un mapa de VAD y energia cada 15 s:
# de 24:00 al final (27:53) no hay voz y la energia es continua -> es la cancion.
# n_hablantes es el valor real (se escucha en el audio), no el estimado; la diarizacion
# automatica sin numero fijo tambien estimo 2 en ambos tramos.
# roles: diarizar() numera por orden de aparicion. Ambos tramos empiezan con el entrevistado
# hablando, asi que H1 = entrevistado y H2 = conductor (verificado leyendo el texto: H2 pregunta).
TRAMOS = {
    "aud_espika_20201121_conversacion": {"inicio": 7 * 60, "fin": 13 * 60, "n_hablantes": 2},
    "aud_espika_20201121_musica": {"inicio": 23 * 60 + 15, "fin": 25 * 60 + 15, "n_hablantes": 2},
}
ROLES = {"H1": "ENTREVISTADO (Peru)", "H2": "CONDUCTOR (Uruguay)"}
# seudonimizacion: el entrevistado se identifica por su rol, no por su nombre
REEMPLAZOS = {"Pepe Arévalo": "[ENTREVISTADO]", "Arévalo": "[ENTREVISTADO]", "Pepe": "[ENTREVISTADO]"}


def main():
    CARPETA_TRAMOS.mkdir(parents=True, exist_ok=True)
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    audio = voz.cargar_audio(MP3)

    voz.MODELOS["faster-whisper"] = voz.MODELOS["faster-whisper"] | {
        "nombre": "faster-whisper small", "hf": REPO_MODELO}
    t = voz.Transcriptor("faster-whisper", device="cpu")

    filas, tiempos = leer_csv(SALIDA), leer_csv(TIEMPOS)
    for ident, tramo in TRAMOS.items():
        x = audio[int(tramo["inicio"] * voz.SR):int(tramo["fin"] * voz.SR)]
        wav = CARPETA_TRAMOS / f"{ident}.wav"
        sf.write(wav, x, voz.SR)
        duracion = len(x) / voz.SR

        t0 = time.perf_counter()
        segs = t.segmentos(x, idioma=IDIOMA)          # VAD activado dentro de segmentos()
        s_asr = time.perf_counter() - t0
        t0 = time.perf_counter()
        segs = voz.diarizar(x, segs, n_hablantes=tramo["n_hablantes"], device="cpu")
        s_diar = time.perf_counter() - t0
        for s in segs:
            s.texto = voz.seudonimizar(s.texto, REEMPLAZOS)
            s.hablante = ROLES.get(s.hablante, s.hablante)
        n_hablantes = tramo["n_hablantes"]

        voz.a_tabla(segs).to_csv(CARPETA_SALIDA / f"{ident}.csv", index=False, encoding="utf-8")
        (CARPETA_SALIDA / f"{ident}.srt").write_text(voz.a_srt(segs), encoding="utf-8")
        (CARPETA_SALIDA / f"{ident}.txt").write_text(voz.a_texto(segs), encoding="utf-8")

        filas[ident] = {
            "id": ident,
            "archivo_audio": wav.name,
            "duracion_seg": round(duracion, 2),
            "idioma": IDIOMA,
            "texto_asr": " ".join(s.texto for s in segs),   # sin marcas de hablante (para el WER)
            "modelo_asr": f"{MODELO_ASR} + diarizacion WeSpeaker",
            "n_hablantes": n_hablantes,
            "texto_referencia": filas.get(ident, {}).get("texto_referencia", ""),
        }
        tiempos[ident] = {
            "id": ident, "archivo_audio": wav.name, "duracion_seg": round(duracion, 2),
            "segundos_computo": round(s_asr, 3), "rtf": round(s_asr / duracion, 4),
            "modelo_asr": MODELO_ASR,
        }
        print(f"{ident}: {duracion:.0f}s audio, ASR {s_asr:.1f}s (RTF {s_asr / duracion:.3f}), "
              f"diarizacion {s_diar:.1f}s, {len(segs)} segmentos, {n_hablantes} hablantes")

    escribir_csv(SALIDA, COLUMNAS, filas)
    escribir_csv(TIEMPOS, COLUMNAS_TIEMPOS, tiempos)
    print(f"-> {CARPETA_SALIDA}/ y {SALIDA} ({len(filas)} filas)")


if __name__ == "__main__":
    main()
