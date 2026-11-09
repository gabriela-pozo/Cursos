# Comparación Modo A (sin herramientas) vs Modo B (MCP + Skills)

Todas las cifras de este documento salen de `evaluacion/resultados.csv` (20 ejecuciones: 10 preguntas × 2 modos). Las respuestas esperadas están fijas en `evaluacion/preguntas.csv`, commiteado antes de ejecutar nada, y la calificación la hizo el script `evaluacion/evaluar.py` según la tolerancia, no a ojo. Los registros completos de cada ejecución están en `evidencias_ia/evaluacion/`.

## Condiciones de la evaluación
- Modelo: `sonnet` en ambos modos; sesiones independientes (`--no-session-persistence`), ejecución secuencial, una ejecución por pregunta y modo.
- **Modo A:** carpeta temporal vacía fuera del repo, sin herramientas, sin MCP y sin skills; Claude solo puede responder de memoria.
- **Modo B:** desde `tarea_4/`, con el MCP `bcrp` y las 3 skills ENAHO; `mcp/cache/` se vació antes de cada pregunta.
- **Plugins en el modo B:** la evaluación usa `--setting-sources project,local`, es decir, solo las skills y ajustes de este proyecto, sin los plugins del usuario. La ejecución de la Parte 3 (informe final) se hizo **antes** de este cambio, con los plugins del usuario cargados. Las respuestas de la Parte 3 no dependieron de ellos (usó solo `mcp__bcrp` y las 3 skills del proyecto), pero el entorno no era idéntico.

## 1. Resumen por modo
| Modo | Correctas | Incorrectas | Sin respuesta ("no sabe") | Tiempo promedio | Costo total |
|---|---|---|---|---|---|
| A (sin herramientas) | 1 | 2 | 7 | 9.5 s | 0.16 USD |
| B (MCP + Skills) | 10 | 0 | 0 | 20.8 s | 0.41 USD |

El modo B fue 2.2 veces más lento (20.8 s frente a 9.5 s) y 2.6 veces más caro (0.41 USD frente a 0.16 USD). No hubo ejecuciones sin respuesta estructurada ni bloqueos de la API del BCRP.

## 2. Errores del modo A
Las dos respuestas incorrectas son errores reales de cifra, no de formato:
- **Pregunta 1** (inflación mensual de Lima, marzo de 2025): dio 1.28 % frente a 0.81 % esperado, y añadió una explicación inventada («impulsada por alimentos y gastos escolares»). Declaró que la cifra era de memoria.
- **Pregunta 3** (inflación a 12 meses, enero de 2020): dio 1.91 % frente a 1.89 % esperado, fuera de la tolerancia de ±0.01.

La **pregunta 8** del modo A fue una respuesta parcial: nombró Ica, pero no dio la tasa (`null`), por eso el script la marcó «no sabe». Las otras 6 respuestas «no sabe» (preguntas 2, 4, 6, 7, 9 y 10) no dieron ninguna cifra.

## 3. Preguntas que mejoraron de A a B
Mejoraron 9 de 10, todas menos la 5:
- De incorrecta a correcta: preguntas 1 y 3.
- De «no sabe» a correcta: preguntas 2, 4, 6, 7, 8, 9 y 10.

La **pregunta 5** (pobreza nacional 2024, 27.6 %) acertó en ambos modos **de memoria, sin herramientas**, probablemente porque es una cifra muy difundida; en el modo B la propia fuente citada dice que no la verificó. Ninguna pregunta empeoró.

## 4. Herramientas usadas en el modo B
- **BCRP (preguntas 1 a 4, 9 y 10):** se usó el MCP del BCRP (`buscar_series`, `serie` o `resumen`).
- **ENAHO (preguntas 6 a 10):** el agente leyó con **Bash** las salidas ya generadas por la skill (`salidas/indicadores.csv`, `salidas/validacion.txt`). **No invocó las skills durante la evaluación.** En las preguntas 9 y 10 combinó MCP y Bash.
- **Pregunta 5:** no usó ninguna herramienta.

## 5. Errores
- **Pregunta 7, modo A:** intentó usar Bash, herramienta deshabilitada (`No such tool available: Bash`). Es el único error de herramienta de las 20 ejecuciones y confirma que el aislamiento del modo A funcionó; respondió «no sabe».
- **Preguntas 8 y 10, modo B:** las cifras salieron de `indicadores.csv`, pero los nombres **Ica** (código 11) y **Cajamarca** (código 06) los asoció a sus códigos de memoria, sin verificarlo con una herramienta. Coincidieron con lo esperado.
- **Preguntas combinadas (9 y 10):** el script no marcó lenguaje causal en ninguna. En el modo B las dos cifras se presentan como datos separados, sin relación de causa; en el modo A no hubo cifras.

## 6. Conclusión
En estas 10 preguntas, con acceso a las series del BCRP y a las salidas de ENAHO el agente acertó las 10; sin herramientas acertó 1, se equivocó en 2 y no supo responder 7. Los dos errores del modo A fueron cifras de memoria dadas con seguridad, y en uno de ellos con una explicación inventada, que es justo el riesgo que las herramientas evitan. A cambio, el modo B fue 2.2 veces más lento y 2.6 veces más caro.

Limitaciones que impiden generalizar:
- Solo 10 preguntas y **una ejecución por modo**: no se midió la variabilidad entre repeticiones.
- Las preguntas se diseñaron **después de construir el sistema**, con respuestas que el sistema ya reproducía en la Parte 3.
- El modo B **tenía salidas ya calculadas** (`indicadores.csv`, `validacion.txt`); las skills no se ejecutaron en la evaluación, así que no se midió su costo de limpieza ni su fiabilidad al correr.
- La única pregunta contestada de memoria con éxito (la 5) muestra que, para cifras muy difundidas, las herramientas no siempre aportan.
- El criterio de causalidad en las combinadas se revisó con un detector de frases simple más lectura manual, no con una prueba exhaustiva.
