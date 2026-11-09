# Trazabilidad de cifras

Generado por `informes/generar_trazabilidad.py`. **Toda cifra del informe debe estar en este archivo**: `informes/verificar_informe.py` falla si el informe contiene un número que no aparece aquí.

- Registro de la ejecución: `evidencias_ia/integracion/ejecucion.jsonl` (sha256 `ac126c881e275fc6`)
- Indicadores ENAHO: `salidas/indicadores.csv` (sha256 `cd679f1ca3c3411c`)
- Las cifras del BCRP se tomaron de las respuestas de las herramientas MCP en ese registro; no se reconsultó el BCRP para obtenerlas. Solo la sección H consulta las fuentes de nuevo, y lo declara.
- Los valores derivados se calculan con los valores sin redondear: restar a mano los valores redondeados puede diferir en una centésima.
- Limitación de esta verificación: acepta un número del informe si aparece en cualquier parte de este archivo; no comprueba que se use en el contexto correcto. Eso lo revisa la lectura del informe.

## F. Orquestación: lo que hizo Claude Code en una sola ejecución

Del registro `evidencias_ia/integracion/ejecucion.jsonl`. Las skills se activaron por la pregunta en lenguaje natural.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| O01 | Herramientas MCP distintas usadas | 5 | – | ReadMcpResourceTool; bcrp:buscar_series; bcrp:graficar_serie; bcrp:resumen; bcrp:serie |
| O02 | Skills distintas usadas | 3 | – | graficando-enaho; limpiando-enaho; mapeando-enaho |
| O03 | Al empezar, salidas/personas_2024.parquet no existía | sí | – | resultado de `ls` en la llamada 2 |
| O04 | Llamadas a herramientas en total | 16 | – | registro de la ejecución |

## A. Inflación a 12 meses, Lima Metropolitana (BCRP)

Serie **PN01273PM**: Índice de precios Lima Metropolitana (var% 12 meses) - IPC. Frecuencia mensual. Fuente: BCRP, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12. Las cifras salen de las respuestas de las herramientas MCP en el registro de la ejecución. Es una tasa a 12 meses ya expresada en %, por eso el cambio entre dos fechas se mide en puntos porcentuales.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| B01 | Observaciones mensuales | 60 | – | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B02 | Primer dato del período (2020-01) | 1.89 | 1.9 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B03 | Último dato del período (2024-12) | 1.97 | 2.0 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B04 | Máximo del período (2022-06) | 8.81 | 8.8 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B05 | Mínimo del período (2020-06) | 1.60 | 1.6 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B06 | Promedio simple de las 60 tasas mensuales | 4.47 | 4.5 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B07 | Cambio entre el primer y el último dato, en puntos porcentuales | 0.08 | 0.1 | `resumen` (llamada 5, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12) |
| B08 | Caída del máximo al último dato, en puntos porcentuales | 6.85 | 6.8 | calculado por este script con los valores de `serie` sin redondear |
| B09 | Amplitud (máximo menos mínimo), en puntos porcentuales | 7.21 | 7.2 | calculado por este script con los valores de `serie` sin redondear |
| B10 | Meses entre el máximo y el último dato | 30 | – | calculado por este script con los valores de `serie` sin redondear |

## A2. Inflación a 12 meses: diciembre de cada año y promedio anual

Valores de `serie` (diciembre) y promedio simple de las tasas mensuales de cada año (calculado por este script).

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| B11 | Año 2020: tasa de diciembre (2020-12) | 1.97 | 2.0 | `serie` (llamada 6) · diciembre |
| B16 | Año 2020: promedio de sus 12 tasas mensuales | 1.83 | 1.8 | calculado por este script con los valores de `serie` sin redondear |
| B12 | Año 2021: tasa de diciembre (2021-12) | 6.43 | 6.4 | `serie` (llamada 6) · diciembre |
| B17 | Año 2021: promedio de sus 12 tasas mensuales | 3.97 | 4.0 | calculado por este script con los valores de `serie` sin redondear |
| B13 | Año 2022: tasa de diciembre (2022-12) | 8.46 | 8.5 | `serie` (llamada 6) · diciembre |
| B18 | Año 2022: promedio de sus 12 tasas mensuales | 7.86 | 7.9 | calculado por este script con los valores de `serie` sin redondear |
| B14 | Año 2023: tasa de diciembre (2023-12) | 3.24 | 3.2 | `serie` (llamada 6) · diciembre |
| B19 | Año 2023: promedio de sus 12 tasas mensuales | 6.31 | 6.3 | calculado por este script con los valores de `serie` sin redondear |
| B15 | Año 2024: tasa de diciembre (2024-12) | 1.97 | 2.0 | `serie` (llamada 6) · diciembre |
| B20 | Año 2024: promedio de sus 12 tasas mensuales | 2.35 | 2.4 | calculado por este script con los valores de `serie` sin redondear |

## A3. Ficha de la serie y gráfico

Ficha leída con el recurso MCP `bcrp://serie/PN01273PM`; gráfico generado por `graficar_serie`.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| R01 | Inicio de la serie en el catálogo | Ene-1950 | – | recurso `bcrp://serie/PN01273PM` (llamada 4) |
| R02 | Última actualización de la serie en el catálogo | 2026-10-08 | – | recurso `bcrp://serie/PN01273PM` |
| R03 | Gráfico del BCRP generado | figuras/bcrp_PN01273PM_2020-01_2024-12.png | – | `graficar_serie` (llamada 7) |

## C. Pobreza monetaria 2024 por área (ENAHO, método oficial del INEI)

Estimaciones ponderadas con `factor07 × mieperho`, generadas por la skill `limpiando-enaho`. Unidad: % de personas.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| E01 | Pobreza monetaria nacional | 27.58 | 27.6 | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) · nacional/Perú |
| E02 | Pobreza monetaria urbana | 24.81 | 24.8 | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) · area/Urbano |
| E03 | Pobreza monetaria rural | 39.30 | 39.3 | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) · area/Rural |
| E04 | Diferencia rural menos urbana, en puntos porcentuales | 14.50 | 14.5 | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E05 | Razón rural / urbana (veces) | 1.58 | 1.6 | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E06 | Hogares de la muestra, área urbana | 22,031 | – | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) |
| E07 | Hogares de la muestra, área rural | 11,660 | – | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) |
| E08 | Pobreza extrema nacional | 5.50 | 5.5 | `salidas/indicadores.csv` (método oficial, hogares, factor07 × mieperho) · pobreza extrema |

## D. Pobreza monetaria 2024 por departamento (ENAHO, método oficial del INEI)

Departamentos por `ubigeo[:2]`; Lima (15) y Callao (07) separados. Unidad: % de personas.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| E09 | Departamentos con dato | 25 | – | `salidas/indicadores.csv` · departamento (método oficial) |
| E10 | Mayor pobreza: Cajamarca (código 06) | 45.01 | 45.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| E11 | Menor pobreza: Ica (código 11) | 6.01 | 6.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| E12 | Brecha entre el mayor y el menor, en puntos porcentuales | 38.99 | 39.0 | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E13 | Departamentos con pobreza mayor que el promedio nacional | 10 | – | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E14 | Departamentos con pobreza menor o igual que el promedio nacional | 15 | – | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E15 | Departamentos con pobreza mayor que la rural nacional | 3 | – | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E16 | Departamentos con pobreza menor que la urbana nacional | 11 | – | calculado por este script con los valores de `indicadores.csv` sin redondear |
| E17 | Lima (código 15) | 27.07 | 27.1 | `salidas/indicadores.csv` · departamento (método oficial) |
| E18 | Callao (código 07) | 33.86 | 33.9 | `salidas/indicadores.csv` · departamento (método oficial) |

## D2. Los 25 departamentos, de mayor a menor pobreza

Una fila por departamento (`salidas/indicadores.csv`); la columna ID lleva el código territorial.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| D06 | Cajamarca (hogares de la muestra: 1,469) | 45.01 | 45.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D16 | Loreto (hogares de la muestra: 1,359) | 42.97 | 43.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D21 | Puno (hogares de la muestra: 1,123) | 39.94 | 39.9 | `salidas/indicadores.csv` · departamento (método oficial) |
| D19 | Pasco (hogares de la muestra: 865) | 38.97 | 39.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D10 | Huánuco (hogares de la muestra: 1,244) | 38.96 | 39.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D07 | Callao (hogares de la muestra: 1,027) | 33.86 | 33.9 | `salidas/indicadores.csv` · departamento (método oficial) |
| D09 | Huancavelica (hogares de la muestra: 1,042) | 33.40 | 33.4 | `salidas/indicadores.csv` · departamento (método oficial) |
| D05 | Ayacucho (hogares de la muestra: 1,160) | 32.76 | 32.8 | `salidas/indicadores.csv` · departamento (método oficial) |
| D20 | Piura (hogares de la muestra: 1,611) | 31.86 | 31.9 | `salidas/indicadores.csv` · departamento (método oficial) |
| D13 | La Libertad (hogares de la muestra: 1,509) | 30.19 | 30.2 | `salidas/indicadores.csv` · departamento (método oficial) |
| D25 | Ucayali (hogares de la muestra: 1,119) | 27.07 | 27.1 | `salidas/indicadores.csv` · departamento (método oficial) |
| D15 | Lima (hogares de la muestra: 4,544) | 27.07 | 27.1 | `salidas/indicadores.csv` · departamento (método oficial) |
| D24 | Tumbes (hogares de la muestra: 842) | 26.90 | 26.9 | `salidas/indicadores.csv` · departamento (método oficial) |
| D01 | Amazonas (hogares de la muestra: 1,243) | 25.75 | 25.7 | `salidas/indicadores.csv` · departamento (método oficial) |
| D23 | Tacna (hogares de la muestra: 1,271) | 23.99 | 24.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D03 | Apurímac (hogares de la muestra: 913) | 23.96 | 24.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D02 | Áncash (hogares de la muestra: 1,393) | 22.77 | 22.8 | `salidas/indicadores.csv` · departamento (método oficial) |
| D22 | San Martín (hogares de la muestra: 1,347) | 22.02 | 22.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D08 | Cusco (hogares de la muestra: 1,230) | 18.54 | 18.5 | `salidas/indicadores.csv` · departamento (método oficial) |
| D12 | Junín (hogares de la muestra: 1,506) | 18.50 | 18.5 | `salidas/indicadores.csv` · departamento (método oficial) |
| D04 | Arequipa (hogares de la muestra: 1,506) | 15.78 | 15.8 | `salidas/indicadores.csv` · departamento (método oficial) |
| D14 | Lambayeque (hogares de la muestra: 1,302) | 14.04 | 14.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D17 | Madre de Dios (hogares de la muestra: 603) | 11.15 | 11.1 | `salidas/indicadores.csv` · departamento (método oficial) |
| D18 | Moquegua (hogares de la muestra: 963) | 10.97 | 11.0 | `salidas/indicadores.csv` · departamento (método oficial) |
| D11 | Ica (hogares de la muestra: 1,500) | 6.01 | 6.0 | `salidas/indicadores.csv` · departamento (método oficial) |

## E. Validación de la base y comparación con la referencia de la sesión 16

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| V01 | Residentes habituales | 108,664 | – | `salidas/validacion.txt` (skill `limpiando-enaho`) |
| V02 | Filas del módulo 02 (miembros) | 117,721 | – | `salidas/validacion.txt` (skill `limpiando-enaho`) |
| V03 | Hogares de la sumaria | 33,691 | – | `salidas/validacion.txt` (skill `limpiando-enaho`) |
| V04 | Verificaciones aprobadas | 16 | – | `salidas/validacion.txt` (skill `limpiando-enaho`) |
| V05 | Verificaciones fallidas | 0 | – | `salidas/validacion.txt` (skill `limpiando-enaho`) |
| V06 | Departamentos que coinciden con la referencia de la sesión 16 | 25 | – | `mapas/comparacion_referencia_2024.csv` (skill `mapeando-enaho`) |
| V07 | Diferencia máxima con la referencia, en puntos porcentuales | 0.049 | – | `mapas/comparacion_referencia_2024.csv` (3 decimales) |
| V08 | Tolerancia por el redondeo de la referencia, en puntos porcentuales | 0.05 | – | constante de `mapear.py` (la referencia está a 1 decimal) |

## H. Verificación independiente de cifras

**Declarado:** estas comparaciones SÍ consultan la fuente de nuevo, por un camino distinto del que usó el agente. BCRP: pedido directo a la API (`urllib`, sin pasar por el servidor MCP). ENAHO: recálculo con pandas desde `sumaria-2024.dta` (`factor07 × mieperho`), sin usar `limpiar.py`. Las cifras del informe vienen de las secciones anteriores, no de esta.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| X01 | [BCRP] Inflación a 12 meses, 2020-01: valor de las herramientas / valor independiente / diferencia / coincide | 1.888356 / 1.888356 / 0.000000 / sí | – | API cruda del BCRP |
| X02 | [BCRP] Inflación a 12 meses, 2022-06 (máximo): valor de las herramientas / valor independiente / diferencia / coincide | 8.812633 / 8.812633 / 0.000000 / sí | – | API cruda del BCRP |
| X03 | [BCRP] Inflación a 12 meses, 2024-12: valor de las herramientas / valor independiente / diferencia / coincide | 1.966303 / 1.966303 / 0.000000 / sí | – | API cruda del BCRP |
| X04 | [BCRP] Promedio simple de los 60 meses: valor de las herramientas / valor independiente / diferencia / coincide | 4.466400 / 4.466356 / 0.000044 / sí | – | API cruda del BCRP |
| X05 | [ENAHO] Pobreza nacional: valor de las herramientas / valor independiente / diferencia / coincide | 27.579500 / 27.579468 / 0.000032 / sí | – | recálculo desde sumaria-2024.dta |
| X06 | [ENAHO] Pobreza urbana: valor de las herramientas / valor independiente / diferencia / coincide | 24.807000 / 24.806989 / 0.000011 / sí | – | recálculo desde sumaria-2024.dta |
| X07 | [ENAHO] Pobreza rural: valor de las herramientas / valor independiente / diferencia / coincide | 39.302800 / 39.302794 / 0.000006 / sí | – | recálculo desde sumaria-2024.dta |
| X08 | [ENAHO] Pobreza en el departamento 06 (Cajamarca): valor de las herramientas / valor independiente / diferencia / coincide | 45.006900 / 45.006897 / 0.000003 / sí | – | recálculo desde sumaria-2024.dta |
| X09 | [ENAHO] Pobreza en el departamento 11 (Ica): valor de las herramientas / valor independiente / diferencia / coincide | 6.014200 / 6.014194 / 0.000006 / sí | – | recálculo desde sumaria-2024.dta |
| X10 | [ENAHO] Pobreza en el departamento 15 (Lima): valor de las herramientas / valor independiente / diferencia / coincide | 27.068900 / 27.068943 / 0.000043 / sí | – | recálculo desde sumaria-2024.dta |
| X11 | [ENAHO] Pobreza en el departamento 07 (Callao): valor de las herramientas / valor independiente / diferencia / coincide | 33.859900 / 33.859893 / 0.000007 / sí | – | recálculo desde sumaria-2024.dta |
| X20 | Periodos de la serie comparados uno a uno con la API cruda | 60 | – | API cruda vs `serie` |
| X21 | Diferencia máxima entre `serie` y la API cruda en esos periodos | 0.000000 | – | API cruda vs `serie` |

## I. Constantes del planteamiento

Números que fija la pregunta de investigación; no son resultados.

| ID | Cifra | Valor (2 dec.) | Valor (1 dec.) | Origen |
|---|---|---|---|---|
| K01 | Años de la pregunta (inicio y fin) | 2020 y 2024 | – | pregunta de investigación acordada |
| K02 | Horizonte de la tasa de inflación, en meses | 12 | – | definición de la serie `PN01273PM` |
| K03 | Departamentos del Perú en el mapa | 25 | – | GeoJSON departamental (`FIRST_IDDP` 01 a 25) |
| K04 | Año de la ENAHO usada | 2024 | – | módulos 34 y 02 de la ENAHO 2024 |

## G. Llamadas a herramientas, en orden

| # | Herramienta | Argumentos | Resultado (inicio) |
|---|---|---|---|
| 1 | `ToolSearch` | `{"query": "select:mcp__bcrp__buscar_series,mcp__bcrp__graficar_serie,mcp__bcrp__resumen,mcp__bcrp__serie,ReadM…` |  |
| 2 | `Bash` | `{"command": "ls salidas figuras mapas 2>&1 / head -50"}` | figuras: bcrp_PD04638PD_2026-09-01_2026-10-30.png bcrp_PN01273PM_2021-01_2026-09.png mapas |
| 3 | `mcp__bcrp__buscar_series` | `{"texto": "ipc lima 12 meses"}` | {"result":[{"codigo":"PN01273PM","nombre":"Índice de precios Lima Metropolitana (var% 12 m |
| 4 | `ReadMcpResourceTool` | `{"server": "bcrp", "uri": "bcrp://serie/PN01273PM"}` | {"contents":[{"uri":"bcrp://serie/PN01273PM","mimeType":"application/json","text":"{\"codi |
| 5 | `mcp__bcrp__resumen` | `{"codigo": "PN01273PM", "desde": "2020-01", "hasta": "2024-12"}` | {"codigo":"PN01273PM","nombre":"Índice de precios Lima Metropolitana (var% 12 meses) - IPC |
| 6 | `mcp__bcrp__serie` | `{"codigo": "PN01273PM", "desde": "2020-01", "hasta": "2024-12"}` | {"codigo":"PN01273PM","nombre":"Índice de precios Lima Metropolitana (var% 12 meses) - IPC |
| 7 | `mcp__bcrp__graficar_serie` | `{"codigo": "PN01273PM", "desde": "2020-01", "hasta": "2024-12"}` | {"ruta":"<PROYECTO>\\figuras\\bcrp_PN01273PM_2020-01_2024-12.png","ruta_relativa":"figuras |
| 8 | `Skill` | `{"skill": "graficando-enaho"}` | Launching skill: graficando-enaho |
| 9 | `Skill` | `{"skill": "limpiando-enaho"}` | Launching skill: limpiando-enaho |
| 10 | `Bash` | `{"command": "ls datos 2>&1 / head; uv run <PROYECTO>/.claude/skills/limpiando-enaho/scripts/limpiar.py 2>&1 / …` | 966-Modulo02 966-Modulo02.zip 966-Modulo34 966-Modulo34.zip descargar.py peru_departamenta |
| 11 | `Bash` | `{"command": "uv run .claude/skills/graficando-enaho/scripts/graficar.py --grafico area 2>&1 / tail -15; echo =…` | OK figuras/enaho2024_pobreza_area.png: urbana 24.81 %, rural 39.30 % (método oficial, hoga |
| 12 | `Skill` | `{"skill": "mapeando-enaho"}` | Launching skill: mapeando-enaho |
| 13 | `Bash` | `{"command": "uv run .claude/skills/mapeando-enaho/scripts/mapear.py 2>&1 / tail -20; ls figuras mapas"}` |  08 Cusco 18.54 18.5 0.041 True 09 Huancavelica 33.40 33.4 0.003 True 10 Huánuco 38.96 39. |
| 14 | `Read` | `{"file_path": "<PROYECTO>\\figuras\\enaho2024_pobreza_area.png"}` |  |
| 15 | `Read` | `{"file_path": "<PROYECTO>\\figuras\\enaho2024_pobreza_departamento.png"}` |  |
| 16 | `Read` | `{"file_path": "<PROYECTO>\\mapas\\pobreza_departamento_2024.png"}` |  |
