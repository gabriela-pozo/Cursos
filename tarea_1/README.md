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
| Zero-shot (40 titulares) | ⟦ ⟧ | ⟦ ⟧ |
| Fine-tuning DistilBERT (test) | ⟦ ⟧ | ⟦ ⟧ |
| Acuerdo LLM-humano | ⟦ ⟧ / 20 | |

## Hallazgos
1. ⟦Escribe aquí el primero, con un número real. Ej.: el fine-tuning mejora al zero-shot en X puntos de F1 macro.⟧
2. ⟦El segundo. Ej.: la categoría con peor F1 es Y y se confunde con Z.⟧

## Limitaciones
1. **Una sola fuente y poco volumen:** 385 titulares de un medio y de dos días; el conjunto de test tiene solo 58, por lo que las métricas tienen mucha incertidumbre y no generalizan a otros medios ni épocas.
2. **Etiquetas por sección:** una nota puede publicarse en una sección que no refleja su tema principal, así que parte del "error" del modelo puede ser ruido de etiquetado.

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

**Dashboard en vivo:** ⟦enlace si se despliega⟧
