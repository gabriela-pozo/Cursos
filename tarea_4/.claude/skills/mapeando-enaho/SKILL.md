---
name: mapeando-enaho
description: Construye el mapa coroplético de la pobreza monetaria por departamento del Perú con la ENAHO 2024 del INEI (25 unidades, Lima y Callao separados), uniendo por código ubigeo[:2] con FIRST_IDDP y comparando con la referencia de la sesión 16; se guarda en mapas/. Úsala cuando pidan un mapa de la pobreza, un mapa por departamento o regiones con la ENAHO. Si falta la base procesada, ejecuta primero limpiando-enaho.
---
# Mapear la pobreza por departamento con la ENAHO 2024

## Antes de mapear: la base procesada

Si **no existe** `salidas/personas_2024.parquet`, usa primero la skill **`limpiando-enaho`** (invócala con la herramienta
Skill) y espera a que termine bien; después sigue con los pasos de abajo. Si `limpiando-enaho` termina con error o
`salidas/validacion.txt` tiene una verificación fallida, **detente** y dilo: no mapees datos no validados.

## Pasos

1. Ejecuta:
   ```
   uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py
   ```
2. El script une los indicadores con `datos/peru_departamental_simple.geojson`, exige 25 unidades con dato, compara cada
   departamento con la referencia de la sesión 16 y guarda:
   - `mapas/pobreza_departamento_2024.png` (el mapa)
   - `mapas/comparacion_referencia_2024.csv` (calculado, referencia y diferencia por departamento)
3. Si el script termina con `ERROR` (faltan unidades, la unión no es 1:1 o un departamento difiere de la referencia más
   de lo que permite su redondeo), **detente**: muestra el mensaje y no corrijas nada para que coincida.
4. Responde con lo que imprimió el script: número de unidades, diferencia máxima con la referencia y la ruta del mapa.
   Mira el PNG antes de darlo por bueno.

## Reglas

- **Une por código, nunca por nombre:** `ubigeo[:2]` (columna `categoria` de `indicadores.csv`) con `FIRST_IDDP`, ambos
  como texto de 2 caracteres. «APURIMAC» no es «Apurímac».
- **Nombres desde el diccionario, no de memoria:** el nombre de cada departamento es la columna `nombre_categoria` de
  `indicadores.csv` (diccionario oficial de `limpiando-enaho`). El script lo contrasta con `NOMBDEP` del GeoJSON y se
  detiene si no coinciden. El mapa rotula cada departamento con su código y su %, y al costado lleva la clave código ·
  nombre · %. Para nombrar un departamento en la respuesta, tómalo de ahí; no lo deduzcas del código.
- **25 unidades con dato, Lima (15) y Callao (07) separados.** El script lo verifica y se detiene si no se cumple.
- **Siempre ponderado:** los valores son el método **oficial del INEI** (hogares, `factor07 × mieperho`), el mismo de
  `validacion.txt`. No recalcules nada a mano.
- **Escala interpretable:** un solo color de claro a oscuro, desde 0, nunca arcoíris. La leyenda dice la unidad
  («% de personas en pobreza monetaria»). El título dice qué pasa, con cifras calculadas, y lleva «Fuente: INEI, ENAHO 2024».
- **Referencia de la sesión 16:** `referencias/pobreza_departamento_2024_sesion16.csv` (en esta carpeta, copiado del repo
  del curso). Está redondeada a 1 decimal, por eso la tolerancia es 0.05 pp.
- **Asociaciones, no causas.** Describe dónde la pobreza es mayor o menor; no expliques por qué. Las estimaciones
  departamentales tienen menos observaciones que las nacionales y no incluyen intervalos de confianza.
- Solo hay datos de 2024.
