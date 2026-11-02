# Reel

Formato 9:16 (1080×1920), 6 escenas, unos 60 s. Estructura: gancho → método → 3 hallazgos → llamado a la acción.

| Archivo | Contenido |
|---|---|
| `guion.json` | Guion por escena (narración, visual, fuente). `guion_con_tiempos.json` agrega tiempos. |
| `subtitulos.srt` | Subtítulos sincronizados con la duración de cada escena. |
| `frames/escena_N.png` | Imagen de cada escena (gráficos y mapa propios, con aviso "Voz generada por IA" y fuente). |
| `narracion_por_escena.txt` | Texto para pegar en la herramienta de voz. |
| `reel.mp4` | Video. **La versión incluida es un preview sin voz.** |

## Cómo generar la versión final con voz

1. `reel/referencia_voz.wav` es tu grabación (`mi_voz.mp4`, 22 s) ya limpia: mono, 24 kHz, volumen normalizado. Úsala como voz de referencia.
2. Con una herramienta de clonación de voz (Qwen3-TTS, VoxCPM2 u otra), genera cada escena a partir de `narracion_por_escena.txt` y guarda los audios como `reel/audio/escena_1.wav` … `escena_6.wav`. Algunas herramientas piden también el texto exacto de la referencia: escribe lo que dices en `mi_voz`.
3. `reel/musica.mp3` ya existe (música original, ver `CREDITOS.md`). Si quieres otra, reemplázala; el script la mezcla a −22 dB, por debajo de la voz.
4. Corre `python scripts/07_make_reel.py reel`. Los subtítulos y los cortes de escena se ajustan solos a la duración real de cada audio.
5. Revisa que la duración total quede entre 45 y 75 s. Si pasa de 75 s, genera la voz con un ritmo un poco más rápido.

El aviso "Voz generada por IA", la fuente de datos y los créditos ya están dibujados en las imágenes.
