---
name: graficando-enaho
description: Grafica la pobreza monetaria de la ENAHO 2024 del INEI con estimaciones ponderadas - pobreza urbana y rural, por sexo y comparación entre departamentos - con título analítico, período, unidades y fuente, guardada en figuras/. Úsala cuando pidan un gráfico, barras o una comparación de la pobreza (urbano/rural, hombres/mujeres, departamentos) con la ENAHO. Si falta la base procesada, ejecuta primero limpiando-enaho.
---
# Graficar la pobreza con la ENAHO 2024

## Antes de graficar: la base procesada

Si **no existe** `salidas/personas_2024.parquet`, usa primero la skill **`limpiando-enaho`** (invócala con la herramienta
Skill) y espera a que termine bien; después sigue con los pasos de abajo. Si `limpiando-enaho` termina con error o
`salidas/validacion.txt` tiene una verificación fallida, **detente** y dilo: no grafiques datos no validados.

## Pasos

1. Elige el gráfico según el pedido:
   - «urbano y rural», «por área» → `area`
   - «por sexo», «hombres y mujeres», «brecha de género» → `sexo`
   - «por departamento», «regiones», «ranking» → `departamento`
   - sin especificar, o «todos» → `todos`
2. Ejecuta:
   ```
   uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --grafico <area|sexo|departamento|todos>
   ```
3. El script guarda `figuras/enaho2024_pobreza_area.png`, `..._sexo.png` y/o `..._departamento.png` e imprime las cifras
   que dibujó. Responde con esas cifras y las rutas; no las recalcules ni las redondees de memoria.
4. Mira el PNG antes de darlo por bueno (título legible, sin textos montados).

## Reglas

- **Siempre ponderado.** Las cifras vienen de `salidas/indicadores.csv`, que genera `limpiando-enaho` con los factores de
  expansión. Nunca hagas promedios simples ni recalcules la pobreza a mano.
- **Método de cada gráfico:**
  - Área y departamento: método **oficial del INEI** (hogares, `factor07 × mieperho`), el mismo de `validacion.txt`.
  - **Sexo: cálculo por personas (`facpob07`)**, porque el sexo es un atributo de la persona. El gráfico lo rotula así y
    avisa que **puede diferir levemente del método oficial**. Si lo comentas, di lo mismo.
- Cada gráfico lleva título analítico con cifras calculadas, período (2024), unidad (% de personas), el `n` muestral y la
  fuente «Fuente: INEI, ENAHO 2024». Las barras parten de cero.
- **Asociaciones, no causas.** Describe diferencias («la pobreza rural fue 14.5 puntos mayor»); no afirmes que un factor
  la causa. Las diferencias pequeñas (por ejemplo por sexo) se presentan sin intervalos de confianza: no digas que son
  «significativas».
- Solo hay datos de 2024. Si piden otro año u otro indicador (extrema, edad), avisa que no está disponible en esta skill.
