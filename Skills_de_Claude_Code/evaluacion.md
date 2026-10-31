# Evaluación: tres pedidos con y sin skills

Cada pedido se corrió con `claude -p` desde la raíz del repo, borrando antes `salidas/personas_2024.parquet` para ver si
las skills se encadenan (`pwsh eval_logs/correr.ps1`; logs en `eval_logs/`). «Sin skills» = `--disallowedTools Skill`.

| Pedido | Modo | Skills activadas | Cifra | ¿Ponderó? | Figura |
|---|---|---|---|---|---|
| ¿Cuál fue la pobreza en Cusco en 2024? | con skills | `limpiando-enaho` | 18.5 % (extrema 2.1 %) | Sí, `facpob07` | — |
| | sin skills | ninguna | 18.5 % (IC 95 % aprox. 14.7–22.4) | Sí, `facpob07` | — |
| Grafica la pobreza urbana y rural | con skills | `graficando-enaho` → `limpiando-enaho` | Urbano 24.7 %, rural 39.4 % | Sí | Barras desde 0, ordenadas, un color, valores, fuente |
| | sin skills | ninguna | Urbano 24.7 %, rural 39.4 % | Sí | La misma (corrió `graficar.py` a mano) |
| Haz un mapa de la pobreza por departamento | con skills | `mapeando-enaho` → `limpiando-enaho` | Cajamarca 45.0 %, Ica 5.9 % | Sí | 25 departamentos, unión por código, escala Reds desde 0 |
| | sin skills | ninguna | Cajamarca 45.0 %, Ica 5.9 % | Sí | La misma (corrió `mapear.py` a mano) |

## Conclusión

- Con skills, las tres se activaron como se esperaba y los pedidos 2 y 3 encadenaron dos skills: al no existir la base
  limpia, `graficando-enaho` y `mapeando-enaho` llamaron primero a `limpiando-enaho`.
- Sin la herramienta Skill, Claude dio las mismas cifras porque encontró los scripts en `.claude/skills/` y los ejecutó
  directamente. Es decir, el valor está en que los scripts fijan el pipeline (filtro de residentes, unión m:1,
  ponderación, unión por código); sin skills llegó al mismo resultado explorando el repo, con más pasos.
- Las cifras departamentales difieren de `referencias/pobreza_departamento_2024.csv` en 0.5 puntos como máximo
  (Puno, Huánuco, Loreto); Ica sale 5.9 % frente a 6.0 %.
