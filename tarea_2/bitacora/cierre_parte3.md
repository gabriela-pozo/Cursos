**Cierre de la bitácora · T2 – Parte 3: Dashboard y despliegue**

## Qué se hizo

**Dashboard público:** https://cursos-fxyrqgctkdjvnxrzaf8vf6.streamlit.app/

`app.py` **solo lee los CSV ya generados**: no ejecuta ningún modelo. `requirements.txt` tiene solo `streamlit`, `pandas` y `plotly`.

- **Al abrir:** el título, una línea con la respuesta a la pregunta y los indicadores con `st.metric`: documentos, minutos de audio, CER, WER y acuerdo LLM-humano.
- **Búsqueda y filtros** por texto, tipo de documento, modelo, fuente y duración. Actualizan los indicadores, los gráficos y las tablas, y el CER y el WER se recalculan sobre lo filtrado.
- **Gráficos de Plotly** con títulos que expresan la conclusión: líneas dudosas por tipo, CER por documento, WER por clip y errores del LLM. Cada tipo de documento tiene un color fijo, y el tipo va también escrito para no depender solo del color.
- **Tabla filtrada descargable en CSV** y comparación con los modelos alternativos.
- **Explorador de documentos:** texto del OCR, transcripción manual, campos del LLM, líneas con su confianza y la imagen, cuando hay una copia publicable en `datos/ejemplos/` (6 imágenes con su atribución).
- **Explorador de audio:** texto, segmentos por hablante y campos del LLM. El audio no se reproduce porque los archivos no se publican y el tramo musical de la entrevista tiene derechos de terceros.
- **Nota al pie** con fuentes, licencias y atribución.

**README.md** con la pregunta, el corpus, las fuentes con licencias y fechas, el método, los resultados, 3 hallazgos, 2 limitaciones y los comandos para ejecutar todo en local.

## Resultados

Los indicadores del dashboard, sin filtros, reproducen los del notebook: CER 0,205, WER 0,045 y acuerdo 8/20. Se probó con `streamlit.testing` en un entorno limpio con solo `requirements.txt`: sin filtros, con búsqueda, con filtros por tipo, sin resultados, y en los exploradores con y sin imagen.
