---
name: graficando-enaho
description: Hace gráficos de barras de la pobreza de la ENAHO del INEI por área (urbana y rural), sexo o grupo de edad, ponderados con facpob07. Úsala cuando pidan graficar, comparar o visualizar la pobreza urbana/rural, de hombres y mujeres o por edad.
argument-hint: [area|sexo|edad]
---
# Graficar la ENAHO

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho`.
2. Corre `uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py <area|sexo|edad>` según la pregunta (sin argumento: `area`).
3. Responde con las cifras que imprime y la ruta del PNG en `figuras/`.

Reglas (el script ya las cumple; respétalas si haces otro gráfico):
- Pondera siempre con `facpob07`.
- Barras que empiezan en cero, ordenadas, un solo color y el valor escrito en cada barra.
- El título dice qué y cuándo; nota al pie «Fuente: INEI, ENAHO 2024».
- PNG a 200 dpi en `figuras/`.
