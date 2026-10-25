# Tarea 2 - Ciencia de Datos con Python

Proyecto individual de Gabriela Pozo (@gabriela-pozo). Repositorio del curso:
https://github.com/gabriela-pozo/Cursos  ·  carpeta de trabajo: `tarea_2/`

**Entrega: domingo, 23:59 (hora de Peru, UTC-5).** Objetivo interno: terminar a las 20:00.

## Que hay que construir

Convertir documentos escaneados o fotografiados (OCR) y entrevistas en audio (ASR)
en un archivo de texto estructurado y buscable, con dashboard publico en Streamlit.

Pregunta de investigacion elegida:

> Los archivos historicos economicos del Peru estan digitalizados, pero
> ¿se puede buscar en ellos? Medicion del error de OCR y ASR, y de cuanta
> revision humana hace falta antes de confiar en las cifras.

Hallazgo de partida ya verificado: las Memorias del BCRP de 1922 y 1923 tienen
**cero caracteres de texto extraible** (son imagenes puras), y las de 1924-1929 si
traen capa de texto pero esta corrompida: en la de 1925 aparecen montos ilegibles
como `Lp. lí)J83,000` donde deberia haber una cifra en libras peruanas.

## Estructura exigida por el enunciado

```
tarea_2/
├── 01_extraccion.ipynb        OCR, transcripcion, limpieza y EDA
├── 02_evaluacion.ipynb        CER/WER, LLM y comparativa de modelos
├── app.py                     dashboard Streamlit
├── requirements.txt           solo lo que necesita la app (sin modelos pesados)
├── README.md                  pregunta, fuentes, 2 hallazgos, 2 limitaciones, comandos
├── .gitignore
├── evidencias_ia/             capturas numeradas 01.png, 02.png, ...
├── datos/
│   ├── documentos.csv
│   ├── transcripciones.csv
│   ├── extraccion_llm.csv
│   ├── fuentes.csv
│   ├── ejemplos/              muestra ligera publicable
│   └── raw/                   NO se versiona
│       ├── documentos/
│       │   ├── paginas/       paginas de PDF -> tipo "impreso"
│       │   ├── fotos/         tipo "foto"
│       │   └── manuscritos/   tipo "manuscrito"
│       └── audio/
└── modelos/
```

Los dos notebooks se entregan **ejecutados, con las salidas visibles en GitHub**.

## Columnas exactas de los CSV (no cambiarlas)

- `documentos.csv`: id, archivo, tipo, fuente, texto_ocr, modelo_ocr, texto_referencia
- `transcripciones.csv`: id, archivo_audio, duracion_seg, idioma, texto_asr, modelo_asr, n_hablantes, texto_referencia
- `extraccion_llm.csv`: id, modalidad, campos_json, modelo_llm, fecha
- `fuentes.csv`: id, modalidad, fuente_url, licencia, acceso

## Corpus (minimos del enunciado y estado real)

| Categoria | Minimo | Estado | Origen |
|---|---|---|---|
| Documentos impresos | 8 | listo | Memorias BCRP 1922 y 1923 (escaneos puros) y folleto "Carta a Agustin Gamarra", Cuzco 1832, del repositorio PUCP (CC0) |
| Fotos con sombra o inclinacion | 8 | 5 de 8 | fotos propias: boletin DIRCETUR Cusco, Sintesis del Reporte de Inflacion marzo 2019, Mapa Estrategico, boleta electronica, etiqueta de envio |
| Manuscritos | 9 | 10, listo | apuntes propios a mano: evaluacion de impacto, mercados laborales con formulas, minimos cuadrados, textileria inca, examen con anotaciones |
| Audio espanol peruano | 30 min, 20 clips | pendiente | OpenSLR 73 con semilla 2026 (ver datos_audio.py) |
| Audio con 2+ hablantes | 1 | pendiente | grabacion propia con consentimiento documentado |

Reglas del enunciado: solo material con licencia que permita el uso, con atribucion
registrada en `fuentes.csv`; seudonimizar datos personales; no rellenar el corpus con
texto sintetico; reportar los archivos descartados.

Licencias ya verificadas:
- BCRP: su portal permite reproducir el contenido citando la fuente.
- Folleto de 1832 (PUCP, Instituto Riva-Aguero): CC0 1.0.
- Guaman Poma en poma.kb.dk (Biblioteca Real de Dinamarca): Public Domain Mark 1.0.
- OpenSLR 73: CC BY-SA 4.0.
- Los documentos de gob.pe NO traen aviso de licencia: usarlos solo como respaldo.

## Requisitos exactos de cada parte (del enunciado)

### Parte 1 — Extraccion, 6 puntos — `01_extraccion.ipynb`

- [ ] **Primera celda**: registrar fecha de ejecucion, fuentes, licencias y versiones de
      los modelos usados.
- [ ] Extraer texto de los **25 documentos** con **PaddleOCR**, documentando los parametros
      elegidos.
- [ ] Transcribir el audio con **VAD + faster-whisper + diarizacion**, y exportar en
      **CSV, SRT y TXT**. No versionar los audios pesados.
- [ ] **Seudonimizar** los datos personales.
- [ ] **Eliminar duplicados por hash** y **reportar los archivos descartados**
      (documentos ilegibles o audios sin voz se descartan y se reemplazan hasta
      cumplir los minimos).
- [ ] **3 graficos con Plotly Express**, cada uno con un **titulo que exprese una
      conclusion** (no "Distribucion de X", sino la conclusion en palabras).
- [ ] **Validar con los casos mas largos y mas cortos** del corpus.
- [ ] Exportar `documentos.csv` y `transcripciones.csv`.

### Parte 2 — Evaluacion, 8 puntos — `02_evaluacion.ipynb`

- [ ] **Muestra fija de 10 documentos y 10 clips**, transcritos **a mano** por la
      estudiante: esa es la referencia. Elegir la muestra y **definir las configuraciones
      ANTES de ver las metricas finales**.
- [ ] **Linea base**: PaddleOCR sin ajustes (medir **CER**) y **faster-whisper `small`
      en CPU** (medir **WER**). **Normalizar** los textos antes de comparar y **excluir
      las marcas de hablante** del calculo del WER.
- [ ] **Extraccion con un LLM**: un prompt que devuelva campos en **JSON** (modalidad,
      tema, resumen, y otros campos solo si aparecen en el documento). Usar **null** para
      lo ausente y **no inventar campos**. Guardar en `extraccion_llm.csv`.
- [ ] **Auditar 20 extracciones al azar** y reportar cuantas aciertan, con ejemplos de error.
      El resultado se informa como `xx/20`.
- [ ] **Comparar un OCR alternativo** (Tesseract, o PaddleOCR-VL) **y otro ASR**
      (Qwen3-ASR, Parakeet o MMS) sobre las mismas muestras, midiendo **CER/WER** y el
      **factor de tiempo real** (segundos de computo por segundo de audio).
- [ ] **Analizar los casos dificiles** (manuscritos, ruido, musica) y presentar una
      **tabla comparativa con una decision justificada**.
- [ ] Bonificacion opcional: quechua de Huaylas con MMS.

Nota: la Parte 2 **no requiere recolectar datos nuevos**; la muestra sale del corpus
de la Parte 1.

### Parte 3 — Dashboard, 4 puntos — `app.py`, `requirements.txt`, `README.md`

- [ ] Titulo, **resumen metodologico** y pestañas o secciones.
- [ ] **Busqueda y filtros** por tipo de documento, modelo, duracion o fuente, que
      **actualicen los graficos y las tablas**.
- [ ] Indicadores con **`st.metric`**: numero de documentos, minutos de audio, CER/WER
      y concordancia LLM-humano.
- [ ] Al menos **2 graficos Plotly** y una **tabla descargable en CSV**.
- [ ] **Exploradores** de documentos y de audios, con texto, campos y hablantes.
      Reproduccion del audio **solo si hay permiso de publicacion**.
- [ ] `README.md` con: pregunta, fuentes con licencias y fechas, **2 hallazgos**,
      **2 limitaciones** y los comandos de ejecucion local.
- [ ] **Despliegue obligatorio en Streamlit Community Cloud**, con enlace publico.
- [ ] El dashboard **no ejecuta modelos pesados**: solo lee los CSV ya generados.

### Flujo en GitHub — 2 puntos

- [ ] Carpeta `tarea_2/` ordenada.
- [ ] Capturas de la conversacion con IA en `evidencias_ia/`, numeradas `01.png`,
      `02.png`, en orden cronologico, sin claves ni datos personales.
- [ ] Los **3 issues de bitacora** creados, documentados y **cerrados** al terminar
      cada etapa.
- [ ] **Commits frecuentes y repartidos en el tiempo**, no todo el ultimo dia.
- [ ] `.gitignore` que excluya `datos/raw/`, los pesos de modelos y las claves.

### Reparto de la nota (20 puntos)

| Parte | Puntos |
|---|---|
| Flujo en GitHub | 2 |
| Parte 1, extraccion | 6 |
| Parte 2, evaluacion | 8 |
| Parte 3, dashboard | 4 |

## Entorno

- Windows 11, PowerShell. **Sin GPU NVIDIA**: PyTorch 2.13.0+cpu. Todo corre en CPU.
- Las librerias estan en el proyecto del curso, no en `tarea_2`:
  `C:\Users\Asus\Documents\GitHub\Data-Science-Python` (grupos `audio` y `docai` ya instalados).
- Por eso todo se ejecuta asi:

```
cd C:\Users\Asus\Documents\GitHub\Cursos\tarea_2
uv run --project C:\Users\Asus\Documents\GitHub\Data-Science-Python python <script>
```

- Para Jupyter: `uv run --project C:\Users\Asus\Documents\GitHub\Data-Science-Python jupyter lab`
- Material de referencia del curso (leerlo antes de escribir codigo de OCR o de voz):
  - `sessions/10-.../paddleocr_documentos_peruanos.ipynb` (PaddleOCR, CER, PaddleOCR-VL)
  - `sessions/13-audio-a-texto/voz.py` (Transcriptor, cargar_audio, tramos_de_voz, diarizar, a_srt, a_texto, seudonimizar, wer, cer)
  - `sessions/13-audio-a-texto/datos.py` (ZipRemoto, descarga por partes de OpenSLR)

## Decisiones ya tomadas (respetarlas)

- **Orientacion activada** en PaddleOCR (`use_doc_orientation_classify=True`): hay cuatro
  imagenes giradas 90 grados (tres paginas de cuaderno y el Reporte de Inflacion).
- **Ids estables**, derivados del nombre del archivo y no del orden, para poder volver a
  correr el OCR tras agregar imagenes sin perder las transcripciones de referencia.
- **Guardar la confianza por linea** del OCR en `datos/ocr_lineas.csv`. No lo pide el
  enunciado, pero de ahi salen los graficos y el analisis de umbral de revision humana.
- **ASR de linea base**: faster-whisper `small` en CPU, con VAD siempre activado.
- El dashboard **no debe ejecutar modelos pesados**: solo lee los CSV ya generados.

## Angulo propio del trabajo (es economia, no solo ingenieria)

1. Medir el error **por tipo de documento**, no solo el promedio: el error no es aleatorio,
   se concentra en manuscritos, fotos con sombra y documentos antiguos.
2. Medir aparte la **exactitud de las cifras** (montos, fechas, porcentajes). Un monto mal
   leido pesa mas que una tilde, y el CER no lo distingue.
3. Estimar en que **umbral de confianza** conviene mandar una linea a revision humana:
   cuanto trabajo se ahorra y cuantos errores se escapan.

## Flujo en GitHub (2 puntos)

Tres issues de bitacora, con estos titulos exactos, que se documentan y se cierran:

1. `T2 – Parte 1: Corpus y extracción (OCR + ASR)`
2. `T2 – Parte 2: Evaluación y extracción estructurada`
3. `T2 – Parte 3: Dashboard y despliegue`

Commits frecuentes y descriptivos, repartidos en el tiempo. Capturas de la conversacion
con IA en `evidencias_ia/`, numeradas y sin claves ni datos personales.

Comentario final en el issue 190 del repositorio del curso:

```
Tarea 2 – Individual
Fuentes: [...]
Estudiante: Nombre Completo (@gabriela-pozo)
Dashboard público (obligatorio): https://...streamlit.app
Carpeta del trabajo: https://github.com/gabriela-pozo/Cursos/tree/main/tarea_2
Resultados Test: WER: 0.xx | CER: 0.xx | Acuerdo LLM-Humano: xx/20
```

## Como trabajar en este repositorio

- Explicar en espanol, con frases cortas, y sin dar por sabido el vocabulario tecnico.
- Antes de un cambio grande, decir que se va a hacer y por que.
- No inventar cifras ni resultados: si algo no se ha medido, decirlo.
- No subir a git los audios crudos, las imagenes pesadas ni claves de API.
