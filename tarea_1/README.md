# Clasificador de titulares peruanos (El Comercio)

Tarea 1 · Ciencia de datos con Python · Estudiante: Gabriela (@gabriela-pozo)

## Pregunta
¿Qué tan bien se pueden clasificar titulares de El Comercio en **política, economía, deportes y ciencia y tecnología**, y qué enfoque conviene: zero-shot, etiquetado con un LLM o un modelo con fine-tuning?

## Datos
- **Medio:** El Comercio (opción B). **Descarga:** 17 y 18 de octubre de 2026.
- **Fuente:** sitemaps de noticias de las secciones política, economía, deporte-total y tecnología (respetando `robots.txt`, con pausa de 1.5 s).
- **Corpus:** 385 noticias tras limpiar duplicados, "Precio del dólar hoy" y secciones fuera de las 4 categorías (`datos/noticias.csv`).
- **Etiqueta:** sección de origen con un mapeo explícito a las 4 categorías.

## Método
1. `01_recoleccion.ipynb`: recolección y limpieza.
2. `02_clasificacion.ipynb`: división estratificada 70/15/15 (seed 42); zero-shot (`joeddav/xlm-roberta-large-xnli`) en 40 titulares; etiquetado con Gemini y auditoría humana de 20 casos; fine-tuning de `distilbert-base-multilingual-cased` (3 épocas). Métrica principal: F1 macro.
3. `app.py`: dashboard en Streamlit.

## Resultados
| Enfoque | Accuracy | F1 macro |
|---|---|---|
| Zero-shot (40 titulares) | 0.825 | 0.820 |
| Fine-tuning DistilBERT (test, 58 titulares) | 0.810 | 0.784 |
| Acuerdo LLM-humano | 16 / 20 (80 %) | |

El LLM (`gemini-3.5-flash-lite`) coincide con la sección de El Comercio en el 91.95 % de los 385 titulares. Zero-shot y fine-tuning se evaluaron sobre conjuntos distintos (40 y 58 titulares), así que la comparación es orientativa.

## Hallazgos
1. **El zero-shot no es peor que el fine-tuning:** F1 macro 0.820 frente a 0.784 (3.6 puntos a favor del zero-shot). Con solo 269 ejemplos de entrenamiento y un test de 58, la diferencia está dentro del ruido: un solo error cambia la accuracy en 1.7 puntos.
2. **El fine-tuning falla sobre todo en ciencia y tecnología:** F1 0.50, con recall de 0.33 (5 de 15 acertados). 7 de esos 15 titulares se clasificaron como economía, por lo que economía tiene la menor precisión (0.667). Política, deportes y economía alcanzan recall de 0.93 a 1.00.

## Limitaciones
1. **Una sola fuente y poco volumen:** 385 titulares de un medio y de dos días; el conjunto de test tiene solo 58, por lo que las métricas tienen mucha incertidumbre y no generalizan a otros medios ni épocas.
2. **Etiquetas por sección:** una nota puede publicarse en una sección que no refleja su tema principal, así que parte del "error" del modelo puede ser ruido de etiquetado.
3. **Cómputo limitado:** sin GPU, el fine-tuning se hizo en CPU y con un modelo pequeño (DistilBERT multilingüe). La cuota gratuita de Gemini (20 peticiones al día por modelo) obligó a etiquetar en lotes de 50 con `gemini-3.5-flash-lite`. El dashboard desplegado puede usar un respaldo ligero (TF-IDF + regresión logística) en lugar del modelo con fine-tuning, y la app indica cuál está usando.

## Cómo ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```
Sin torch, el clasificador en vivo usa un **respaldo ligero** (TF-IDF + regresión logística) y la app lo indica. Para usar el modelo con fine-tuning:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers==5.20.1
```
El modelo se descarga de Hugging Face Hub (`REPO_HF` en `app.py`); los pesos no se versionan por el límite de 100 MB de GitHub.

## Estructura
```
01_recoleccion.ipynb   02_clasificacion.ipynb   app.py   requirements.txt
datos/  noticias.csv · etiquetas_llm.csv · split.csv · predicciones_test.csv
modelo/ metricas.json · etiquetas.json · matriz_confusion.png
```

**Dashboard en vivo:** https://titulares-pe-gabriela.streamlit.app
