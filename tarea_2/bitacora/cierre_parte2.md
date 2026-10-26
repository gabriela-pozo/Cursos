**Cierre de la bitácora · T2 – Parte 2: Evaluación y extracción estructurada**

## Qué se hizo

- **Muestra fija** de 10 documentos (4 impresos, 3 fotos, 3 manuscritos) y 10 clips (semilla `20261025`), elegida y configurada antes de calcular cualquier métrica. La referencia es una transcripción manual propia (`datos/referencias_*.md`).
- **Normalización** antes de comparar: minúsculas, sin puntuación y con unión de palabras partidas por guion. Para el WER se quitan las marcas de hablante y las cifras se pasan a palabras.
- **Recorte por posición** de las zonas que la referencia omite (gráficos, tabla y código QR), para no castigar al OCR por lo que no se transcribió.
- **Extracción con un LLM** (Qwen2.5-0.5B-Instruct, local, en CPU) a JSON con un esquema cerrado y `null` para lo ausente. Resultado en `datos/extraccion_llm.csv` (430 filas).
- **Auditoría a mano** de 20 extracciones al azar (`datos/auditoria_llm.md`).
- **Comparación de modelos:** PaddleOCR-VL y Parakeet TDT 0.6B v3 (`modelos_alternativos.py`).

## Resultados de la línea base

| Métrica | Valor |
|---|---|
| CER, 10 documentos (PP-OCRv6) | **0,205** (impresos 0,231 · fotos 0,191 · manuscritos 0,134) |
| WER, 10 clips (faster-whisper `small`) | **0,045** |
| Cifras exactas (montos, fechas y %) | **66/75** (88 %); los montos son los que peor salen: 21/26 |
| Acuerdo LLM-humano | **8/20** |

- **El CER no es parejo.** Dos páginas concentran el error. La carta p003 da 0,90 porque el clasificador de orientación la gira 180°; sin ella, los impresos quedan en 0,023. En el Reporte de Inflación, al menos el 96 % del error es orden de lectura de las dos columnas: con un orden por columnas el CER baja de 0,46 a 0,02.
- **Un CER bajo no garantiza cifras útiles.** Las Memorias del BCRP tienen CER 0,01-0,02 y aun así 4 montos salieron mal (`642,901` → `642,90l`).
- **El LLM omite más de lo que inventa.** De los 12 fallos, 10 son omisiones y 2 invenciones. Las dos invenciones convierten una pregunta en afirmación, y eso pasa en 20 de las 24 preguntas del corpus que tienen resumen. Los fallos se concentran en los textos cortos, no en los de mayor error de ASR. Además, el modelo introduce errores propios, como «peruinos» sobre un OCR limpio.

## Comparación de modelos

| Modelo | Muestra | Error | Costo |
|---|---|---|---|
| PP-OCRv6 | 4 documentos | CER 0,296 | 20 s por página |
| PaddleOCR-VL | 4 documentos | CER 0,162 | 483 s por página |
| faster-whisper `small` | 10 clips | WER 0,045 | RTF 0,36 |
| Parakeet TDT 0.6B v3 | 10 clips | WER 0,045 | RTF 0,23 |

**Decisión:**
- PaddleOCR-VL **solo para manuscritos** (CER 0,115 → 0,058), con revisión humana, porque escribe palabras verosímiles pero falsas.
- PP-OCRv6 para impresos y boletas. En la boleta, PaddleOCR-VL empeora (0,114 → 0,185) porque separa cada monto de su etiqueta.
- PP-OCRv6 con orden por columnas para las páginas a dos columnas.
- Se mantiene faster-whisper: empata en WER, ya procesa todo el corpus con VAD y diarización, y cambiar obligaría a re-transcribir 402 audios.

`02_evaluacion.ipynb` está ejecutado y con las salidas visibles.
