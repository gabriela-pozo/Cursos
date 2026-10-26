# De documentos escaneados y audio a texto buscable: evaluación sobre un corpus peruano

**Tarea 2 · Ciencia de Datos con Python**
Gabriela Pozo ([@gabriela-pozo](https://github.com/gabriela-pozo))

**Dashboard público:** https://cursos-fxyrqgctkdjvnxrzaf8vf6.streamlit.app/

---

## 1. La pregunta

> ¿Se pueden convertir documentos escaneados y entrevistas en audio en un archivo
> de texto estructurado y buscable?

La respuesta corta de este trabajo es que **sí se pueden convertir, pero no siempre
se puede confiar en el resultado**. Lo que sigue mide cuánto error sobrevive en cada
etapa del proceso (lectura de imágenes, transcripción de voz y extracción de campos
con un modelo de lenguaje) y cuánta revisión humana hace falta antes de usar ese
texto como dato.

El caso que motivó la pregunta es concreto. Las Memorias del Banco de Reserva del
Perú de 1922 y 1923 están publicadas en el portal del BCRP y **no contienen una sola
letra de texto extraíble**: son imágenes. Las de 1924 a 1929 sí traen texto, pero
deteriorado: donde debería figurar un monto en libras peruanas, el archivo dice
`Lp. lí)J83,000`. Están digitalizadas y, aun así, no se pueden buscar.

## 2. El corpus

28 documentos y 42 minutos de audio en español peruano, más una entrevista de radio
con dos hablantes.

| Modalidad | Cantidad | Contenido |
|---|---|---|
| Documentos impresos | 8 páginas | Memorias del BCRP de 1922 y 1923, y el folleto *Carta escrita a Don Agustín Gamarra* (Cuzco, 1832) |
| Fotos con sombra o inclinación | 10 | Boletín estadístico de turismo de DIRCETUR Cusco, Síntesis del Reporte de Inflación de marzo de 2019, mapa estratégico del sector turismo, página de un texto sobre regulación económica, boleta electrónica, etiqueta de envío, carta de precios, horario del Banco de la Nación, letrero de negocios de Av. Sol y afiche de tránsito de la Municipalidad del Cusco |
| Manuscritos | 10 | Apuntes propios escritos a mano sobre evaluación de impacto, mercados laborales, mínimos cuadrados y textilería inca |
| Audio | 400 clips y 1 entrevista | OpenSLR 73 (selección con semilla 2026) y un bloque de Espika FM con dos hablantes, en 2 tramos (conversación y cierre con música) |

Los mínimos exigidos eran 8 documentos impresos, 8 fotos, 9 manuscritos y 30 minutos
de audio con al menos 20 clips. El corpus los cumple.

### Fuentes y licencias

| Fuente | Licencia | Fecha de consulta |
|---|---|---|
| Memorias del BCRP, 1922-1929 | Reproducción permitida citando la fuente, según las [condiciones de uso del portal](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/condiciones-de-uso) | 24/10/2026 |
| *Carta escrita a Don Agustín Gamarra*, Cuzco 1832, Instituto Riva-Agüero (PUCP) | CC0 1.0 | 24/10/2026 |
| OpenSLR 73, español peruano | CC BY-SA 4.0 | 24/10/2026 |
| Espika FM 90.7, «Al mundo le falta un tornillo», 21/11/2020 | CC BY-SA 4.0 | 24/10/2026 |
| Fotos y manuscritos | Capturas propias, sin datos personales reales | 24 y 25/10/2026 |

El detalle por archivo, con su enlace y su forma de acceso, está en `datos/fuentes.csv`.

## 3. El método

```
imagen o audio  →  OCR / ASR con detección de voz  →  seudonimización
                →  deduplicado por hash  →  extracción de campos con un LLM
                →  medición contra una referencia transcrita a mano
```

| Etapa | Modelo | Configuración |
|---|---|---|
| Lectura de imágenes, línea base | PP-OCRv6 (PaddleOCR) | `engine=transformers`, corrección de orientación activada, CPU |
| Lectura de imágenes, alternativo | PaddleOCR-VL | CPU, sobre una submuestra por su costo |
| Transcripción de voz, línea base | faster-whisper `small` | CTranslate2 int8, CPU, detección de voz (VAD Silero) siempre activa |
| Transcripción de voz, alternativo | Parakeet TDT 0.6B v3 | CPU |
| Extracción de campos | Qwen2.5-0.5B-Instruct | transformers, CPU, float32, decodificación sin azar |

La referencia con la que se mide el error es una **transcripción manual de 10
documentos y 10 clips**, hecha sin consultar la salida de los modelos. La muestra y
las configuraciones se fijaron antes de calcular ninguna métrica.

## 4. Resultados

| Métrica | Valor |
|---|---|
| Error por carácter (CER), 10 documentos | 0,205 |
| Error por palabra (WER), 10 clips | 0,045 |
| Cifras leídas de forma exacta | 66 de 75 (88 %) |
| Acuerdo entre el LLM y la revisión humana | 8 de 20 |

Comparación entre modelos. El OCR se comparó en una **submuestra de 4 documentos** (un impreso
limpio, un manuscrito, la boleta y la página a dos columnas), porque PaddleOCR-VL en CPU tarda
minutos por página; por eso su CER no es el mismo que el de los 10 documentos. El audio se comparó
en los mismos 10 clips.

| Modelo | Muestra | Error | Costo |
|---|---|---|---|
| PP-OCRv6 | 4 documentos | CER 0,296 | 20 s por página |
| PaddleOCR-VL | 4 documentos | CER 0,162 | 483 s por página |
| faster-whisper `small` | 10 clips | WER 0,045 | 0,36 s por segundo de audio |
| Parakeet TDT v3 | 10 clips | WER 0,045 | 0,23 s por segundo de audio |

## 5. Tres hallazgos

### 5.1. Un error bajo por carácter no garantiza cifras utilizables

Las Memorias del BCRP se leen casi sin fallos: CER de 0,01 a 0,02, con una confianza
declarada por el modelo de 0,99. Y, aun así, **cuatro montos salieron equivocados**.
El caso más claro es `642,901`, que se leyó `642,90l`, con una ele en lugar del uno
final.

En la muestra de 10 documentos, 66 de 75 cifras se leyeron de forma exacta, y los montos
son la clase que peor sale: 21 de 26. Un error de un
carácter dentro de una cifra pesa mucho más que veinte tildes mal puestas, y **el CER
no distingue entre ambos casos**. Para usar un archivo como fuente de datos
numéricos, la métrica habitual mide lo que menos importa.

### 5.2. El modelo más preciso no es el más conveniente

En la submuestra de 4 documentos, PaddleOCR-VL reduce el error casi a la mitad (CER 0,162
frente a 0,296), pero cuesta **24 veces más tiempo por página**. La mejora no es pareja: viene
del manuscrito (0,115 → 0,058) y de la página a dos columnas, cuyo orden de lectura respeta; en el
impreso limpio empata y en la boleta empeora (0,114 → 0,185), porque separa cada monto de su
etiqueta. Y en los manuscritos se equivoca de una forma particular: produce texto que suena
verosímil y que, por eso mismo, cuesta detectar (escribe «Colesterol» donde dice «Colegio»).

Un error evidente se corrige; uno verosímil se publica. Cuando después de esa lectura
viene un modelo de lenguaje que construye sobre el texto, el error verosímil resulta
el más caro de todos.

### 5.3. El modelo de lenguaje convierte preguntas en afirmaciones

La extracción con Qwen2.5-0.5B acierta en **8 de 20** casos auditados a mano. Las dos
invenciones de la muestra son el mismo error: el texto es una pregunta y el resumen la
convierte en una afirmación que nadie dijo. No son casos aislados: en todo el corpus de
clips, de las **24 preguntas** a las que el modelo les escribió un resumen, **20** quedaron
como afirmación (cuenta automática, así que es una cota superior). Por ejemplo:

> «¿Puedes verificar si hay alguna piscina olímpica cerca de la casa de Pedro?»
> → «Pedro tiene una piscina en su casa».

Frente al error de la entrada, el modelo es impredecible. Con el ASR equivocado
(«pisa vegetariana» por *pizza*), a veces amplifica el error e inventa datos sobre la
«pisa», y otras veces esquiva el tramo dañado. Y con una entrada limpia también falla
por su cuenta: en la Memoria de 1923, cuyo OCR tiene un CER de 0,009 y solo dice «Perú»,
el resumen habla de «bancos **peruinos**». Esa errata la introdujo el modelo; no venía
del OCR. Por eso la cadena OCR/ASR → LLM no es confiable sin revisión humana.

## 6. Dos limitaciones

### 6.1. La muestra es pequeña y la referencia humana también tiene error

La medición se hizo sobre 10 documentos y 10 clips. Los resultados son
**exploratorios y no se pueden generalizar** al conjunto de los archivos peruanos.

Además, la transcripción manual que sirve de referencia contenía erratas, detectadas
al compararla con la salida de los modelos y con el texto oficial de OpenSLR. Se corrigieron
en parte: el WER bajó de 0,074 a 0,045 tras corregir el audio. Quedan algunas, como
«Bnaco» o «infividuo» en los documentos y dos clips de audio, así que el CER de los impresos
limpios está algo sobrestimado. Conviene decirlo con claridad: parte del error medido es
humano, no del modelo.

### 6.2. El audio es habla leída, no conversación espontánea

Los 400 clips de OpenSLR 73 son frases leídas por una sola persona en condiciones
controladas, es decir, el caso fácil. La única conversación real del corpus es la
entrevista de Espika FM, cuyo conductor además no es peruano. Un corpus de
entrevistas de campo daría un error bastante mayor.

A esto se suma que todo el procesamiento corrió **sin tarjeta gráfica**, lo que
obligó a evaluar PaddleOCR-VL sobre una submuestra de documentos.

## 7. Cómo ejecutarlo

Las librerías están en el repositorio del curso, no en esta carpeta. Primero:

```bash
cd <ruta>/Data-Science-Python
uv sync --group hf --group llm --group audio --group docai
```

Después, desde `tarea_2/`:

```bash
# Reunir el corpus
uv run --project <ruta>/Data-Science-Python python datos_audio.py
uv run --project <ruta>/Data-Science-Python python extraer_paginas.py

# Extraer el texto
uv run --project <ruta>/Data-Science-Python python ocr_documentos.py
uv run --project <ruta>/Data-Science-Python python transcribir_audio.py
uv run --project <ruta>/Data-Science-Python python transcribir_entrevista.py
uv run --project <ruta>/Data-Science-Python python extraccion_llm.py

# Modelos alternativos (PaddleOCR-VL tarda varios minutos por página en CPU)
uv run --project <ruta>/Data-Science-Python python modelos_alternativos.py

# Abrir los notebooks
uv run --project <ruta>/Data-Science-Python jupyter lab
```

El dashboard no ejecuta ningún modelo: solo lee los CSV ya generados, por lo que se
puede levantar con muy pocas dependencias.

```bash
uv run --no-project --with-requirements requirements.txt streamlit run app.py
```

## 8. Contenido de la carpeta

| Archivo | Qué contiene |
|---|---|
| `01_extraccion.ipynb` | Lectura de imágenes y audio, limpieza y gráficos |
| `02_evaluacion.ipynb` | CER, WER, extracción con LLM y comparación de modelos |
| `app.py` | Dashboard de Streamlit |
| `requirements.txt` | Dependencias del dashboard |
| `datos/documentos.csv` | Corpus de documentos con su texto |
| `datos/transcripciones.csv` | Corpus de audio con su texto |
| `datos/extraccion_llm.csv` | Campos extraídos por el modelo de lenguaje |
| `datos/fuentes.csv` | Fuente, licencia y acceso de cada archivo |
| `datos/referencias_*.md` | Transcripciones manuales de la muestra de evaluación |
| `datos/auditoria_llm.md` | Auditoría a mano de 20 extracciones del LLM |
| `datos/metricas_linea_base.csv`, `datos/comparativa_modelos.csv` | CER, WER y comparación de modelos que lee el dashboard |
| `datos/ejemplos/` | Copias reducidas de 6 imágenes publicables, con su atribución en `LEEME.md` |
| `modelos_alternativos.py` | PaddleOCR-VL y Parakeet sobre la muestra |
| `evidencias_ia/` | Capturas del trabajo asistido por IA |

Las imágenes y los audios originales están en `datos/raw/`, que no se versiona por su
tamaño.
