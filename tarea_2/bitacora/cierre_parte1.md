**Cierre de la bitácora · T2 – Parte 1: Corpus y extracción (OCR + ASR)**

## Qué se hizo

**Corpus.** 28 documentos y 50 minutos de audio, todos con fuente y licencia registradas en `datos/fuentes.csv`.

| Categoría | Mínimo | Final | Origen |
|---|---|---|---|
| Impresos | 8 | 8 | Memorias del BCRP 1922 y 1923 (escaneos sin capa de texto) y folleto *Carta escrita a Don Agustín Gamarra*, 1832 (PUCP, CC0) |
| Fotos con sombra o inclinación | 8 | 10 | Capturas propias: boletín de DIRCETUR Cusco, Síntesis del Reporte de Inflación del BCRP, boleta, etiqueta de envío, carta de precios, horario del Banco de la Nación, letrero de Av. Sol, afiche municipal, entre otras |
| Manuscritos | 9 | 10 | Apuntes propios |
| Audio en español peruano | 30 min, 20 clips | 42,0 min, 400 clips | OpenSLR 73 (CC BY-SA 4.0), elegidos con semilla 2026 |
| Audio con 2 o más hablantes | 1 | 1 entrevista (2 tramos, 8 min) | Espika FM 90.7 (CC BY-SA 4.0) |

**Extracción.**
- OCR con **PaddleOCR PP-OCRv6** (`ocr_documentos.py`), con corrección de orientación activada. Se guardan 1376 líneas con su confianza en `datos/ocr_lineas.csv`.
- Transcripción con **faster-whisper `small` en CPU, con VAD**. La entrevista lleva además diarización con WeSpeaker, y se exporta en CSV, SRT y TXT (`datos/entrevistas/`). El factor de tiempo real global de los clips es 0,37.
- **Seudonimización:** se buscaron DNI, celulares, correos y RUC de persona natural. Los dos hallazgos (un DNI genérico y el teléfono de una empresa) se revisaron a mano y no son datos personales. El nombre del entrevistado se reemplazó por `[ENTREVISTADO]`.
- **Duplicados por hash SHA-256:** se revisaron 430 archivos y no hubo ningún duplicado. `datos/descartes.csv` registra las 46 páginas que quedaron fuera por selección, no por ilegibles.
- **Validación** con los casos más largos y más cortos: nada se pierde al unir líneas. El texto corto sirve de alarma: el letrero de Av. Sol devuelve solo `V.SOL 3`.
- Se exportaron `documentos.csv` y `transcripciones.csv` con las columnas exactas del enunciado.

## Resultados

Los 3 gráficos de Plotly de `01_extraccion.ipynb` tienen títulos que expresan la conclusión:
1. Una de cada tres líneas de manuscrito es dudosa (35 %), más del doble que en impresos y fotos (16 %).
2. Dos páginas del folleto de 1832 concentran el 78 % de las líneas dudosas de los impresos; las Memorias del BCRP casi no dudan.
3. Subir el umbral de confianza de 0,90 a 0,95 lleva los manuscritos de 35 % a 60 % de líneas por revisar, mientras que los impresos casi no cambian.

`01_extraccion.ipynb` está ejecutado y con las salidas visibles.
