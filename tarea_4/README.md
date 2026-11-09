# Tarea 4: agente de investigación socioeconómica (MCP del BCRP + Skills de la ENAHO 2024)

## 1. Objetivo

Construir un agente de Claude Code que combine dos tipos de herramientas:

- un **servidor MCP** (FastMCP) con series oficiales del Banco Central de Reserva del Perú (BCRP);
- tres **Skills** de Claude Code que procesan, grafican y mapean la pobreza monetaria de la ENAHO 2024 del INEI.

Con ambos, el agente responde la pregunta de investigación: *¿cómo evolucionó la inflación a 12 meses en Lima entre 2020 y 2024, y qué diferencias territoriales (urbano/rural y departamental) presentaba la pobreza monetaria en 2024?* El análisis es descriptivo: no estima ninguna relación entre inflación y pobreza.

Reglas del proyecto: ninguna cifra se escribe a mano, la ENAHO siempre se pondera, las diferencias entre grupos no se presentan como causas y, si una validación o una herramienta falla, se informa el error en lugar de inventar datos.

## 2. Arquitectura del agente

```
Claude Code (claude -p)
├── MCP bcrp  (mcp/server.py, por stdio, declarado en .mcp.json)
│     └── API y catálogo del BCRP → caché en mcp/cache/ y mcp/datos/
└── Skills  (.claude/skills/)
      limpiando-enaho ──► salidas/personas_2024.parquet, indicadores.csv, validacion.txt
            ├── graficando-enaho ──► figuras/
            └── mapeando-enaho  ──► mapas/
```

- Las cuentas las hacen scripts de Python, no el modelo; cada cifra sale de una llamada repetible.
- `graficando-enaho` y `mapeando-enaho` dependen de `limpiando-enaho`: si falta `salidas/personas_2024.parquet`, la ejecutan primero.
- `informes/` genera la trazabilidad de cifras y verifica el informe final.

Estructura del directorio:

| Carpeta | Contenido |
|---|---|
| `mcp/` | Servidor MCP (`server.py`) y sus pruebas (`test_server.py`) |
| `.claude/skills/` | Las tres Skills y sus scripts |
| `datos/` | `descargar.py`; los datos descargados no se suben (`.gitignore`) |
| `salidas/` | Indicadores y validación de la ENAHO (el parquet no se sube) |
| `figuras/`, `mapas/` | Gráficos y mapa generados |
| `evaluacion/` | Preguntas y script de evaluación |
| `informes/` | Informe final, trazabilidad y verificadores |
| `evidencias_ia/` | Registros de las sesiones y ejecuciones con IA |

## 3. Herramientas MCP

Servidor `bcrp` (`mcp/server.py`):

| Elemento | Tipo | Qué hace |
|---|---|---|
| `buscar_series` | herramienta | Busca series por palabras en el catálogo oficial y devuelve código, nombre, frecuencia e inicio |
| `serie` | herramienta | Devuelve los datos período por período entre dos fechas, con la URL de la fuente |
| `resumen` | herramienta | Calcula con Python el primero, el último, el cambio, la variación, el promedio, el máximo y el mínimo |
| `graficar_serie` | herramienta propia | Dibuja la serie y guarda un PNG en `figuras/` con título, código, período, unidad y fuente |
| `bcrp://serie/{codigo}` | recurso | Ficha de la serie leída del catálogo local |
| `informe` | prompt | Receta para elaborar un informe breve citando código, período y fuente |

Formato de fechas: mensual `2025-01`, trimestral `2025-T1`, diaria `2026-10-15` (o `2026-10` para el mes completo) y anual `2025`.

Las solicitudes a la API usan caché en memoria y en disco (24 h), pausa mínima entre pedidos y hasta 6 reintentos. Los valores `n.d.` se omiten; nunca se rellenan.

## 4. Las tres Skills

| Skill | Qué hace | Salidas |
|---|---|---|
| `limpiando-enaho` | Une los módulos 34 (sumaria) y 02 (miembros), filtra residentes habituales, construye departamento (`ubigeo[:2]`), área y sexo, y valida la base (16 verificaciones) | `salidas/personas_2024.parquet`, `salidas/indicadores.csv`, `salidas/validacion.txt` |
| `graficando-enaho` | Grafica la pobreza por área, sexo y departamento, con estimaciones ponderadas | `figuras/enaho2024_pobreza_{area,sexo,departamento}.png` |
| `mapeando-enaho` | Mapa coroplético por departamento (25 unidades, Lima y Callao separados); une por código `ubigeo[:2]` con `FIRST_IDDP` y compara con la referencia de la sesión 16 | `mapas/pobreza_departamento_2024.png`, `mapas/comparacion_referencia_2024.csv` |

Si una validación esencial falla, `limpiar.py` termina con `ERROR` y no se genera ninguna base.

Resultados de la última validación (`salidas/validacion.txt`: 16 verificaciones aprobadas, 0 fallidas):

| Indicador | Obtenido | Referencia |
|---|---|---|
| Residentes habituales | 108,664 de 117,721 filas | 108,664 |
| Hogares | 33,691 | 33,691 |
| Unidades territoriales (`ubigeo[:2]`) | 25, de 01 a 25 (Lima 15 y Callao 07 separados) | 25 |
| Pobreza monetaria nacional (método oficial) | 27.58 % | 27.6 % ± 0.1 pp |
| Pobreza monetaria urbana (método oficial) | 24.81 % | 24.8 % ± 0.1 pp |
| Pobreza monetaria rural (método oficial) | 39.30 % | 39.3 % ± 0.1 pp |

## 5. Fuentes y enlaces de descarga

| Fuente | Uso | Enlace |
|---|---|---|
| BCRP, Estadísticas de series: API | Datos de las series | https://estadisticas.bcrp.gob.pe/estadisticas/series/api |
| BCRP, catálogo de series | Búsqueda de códigos (se descarga solo, en `mcp/datos/`) | https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata |
| INEI, ENAHO 2024, módulo 34 (sumaria), STATA | Pobreza monetaria | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip |
| INEI, ENAHO 2024, módulo 02 (miembros), STATA | Sexo, residencia habitual | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip |
| GeoJSON departamental (repositorio del curso) | Mapa | https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson |

Serie principal: `PN01273PM`, *Índice de precios Lima Metropolitana (var% 12 meses) - IPC*.

`uv run datos/descargar.py` baja y descomprime los datos del INEI y el GeoJSON en `datos/`. Si el INEI bloquea la descarga automática, baje los dos zip a mano desde los enlaces anteriores y descomprima cada uno en `datos/966-Modulo34/` y `datos/966-Modulo02/`.

## 6. Instalación con uv

Requiere Python 3.11 o superior y [uv](https://docs.astral.sh/uv/). Desde la carpeta `tarea_4/`:

```
uv sync
```

Las dependencias (`fastmcp`, `pandas`, `pyarrow`, `geopandas`, `matplotlib`, `pytest`, `httpx`) están en `pyproject.toml` y `uv.lock`.

## 7. Cómo conectar el MCP a Claude Code

El archivo `.mcp.json` ya declara el servidor. Basta abrir Claude Code desde `tarea_4/` y aprobar el servidor `bcrp`. Para registrarlo manualmente:

```
claude mcp add --scope project bcrp -- uv run mcp/server.py
```

Compruebe la conexión con `claude mcp list` o con `/mcp` dentro de Claude Code. La primera vez, el servidor descarga el catálogo (unos 7 MB).

## 8. Comandos para reproducir

Desde `tarea_4/`:

```
# Datos
uv run datos/descargar.py

# Procesamiento de la ENAHO (también lo ejecuta la skill limpiando-enaho)
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py

# Gráficos (area, sexo, departamento o todos) y mapa
uv run .claude/skills/graficando-enaho/scripts/graficar.py --grafico todos
uv run .claude/skills/mapeando-enaho/scripts/mapear.py

# Pruebas del servidor MCP (10 pruebas; requieren conexión a internet)
uv run pytest

# Trazabilidad y verificación del informe
uv run informes/generar_trazabilidad.py
uv run informes/verificar_informe.py

# Evaluación: modo A (sin herramientas) y modo B (MCP + Skills) sobre las 10 preguntas de evaluacion/preguntas.csv
uv run evaluacion/evaluar.py --modos A B
uv run evaluacion/evaluar.py --modos A B --ids 4    # prueba con una sola pregunta
```

La evaluación invoca `claude -p` por cada pregunta y modo, y escribe `evaluacion/resultados.csv`. Los registros de cada ejecución quedan en `evidencias_ia/evaluacion/`.

## 9. Resultados de la evaluación

Resultados de `evaluacion/resultados.csv`: 10 preguntas en cada modo, con el modelo `sonnet`. Detalle de las condiciones en [`evaluacion/comparacion.md`](evaluacion/comparacion.md).

| | Modo A (sin herramientas) | Modo B (MCP + Skills) |
|---|---|---|
| Respuestas correctas | 1 de 10 | 10 de 10 |
| Incorrectas | 2 | 0 |
| «No sabe» | 7 | 0 |
| Tiempo promedio por pregunta | 9.5 s | 20.8 s |
| Costo total | US$ 0.16 | US$ 0.41 |

- **Mejoraron (A → B):** 9 preguntas (1, 2, 3, 4, 6, 7, 8, 9 y 10). En el modo A, las preguntas 1 y 3 se respondieron con cifras equivocadas y las otras siete quedaron en «no sabe».
- **Sin cambio:** la pregunta 5 (pobreza nacional 2024) fue correcta en ambos modos.
- **Empeoraron:** ninguna.
- **Costo en tiempo:** el modo B tardó más en todas las preguntas, unas 2.2 veces el tiempo del modo A en promedio.
- **Error registrado:** en la pregunta 7 del modo A, el modelo intentó usar `Bash`, que estaba deshabilitado; la columna `errores` lo anota.

## 10. Limitaciones y problemas encontrados

- **Bloqueos de la API del BCRP.** La API bloquea al azar pedidos seguidos y responde una página HTML en lugar de JSON. Por eso el servidor aplica pausa entre pedidos, reintentos con espera creciente y caché. Si tras 6 intentos no hay datos, devuelve un error que sugiere reintentar en unos minutos; no inventa valores.
- **Título de `graficar_serie`.** El título automático describe solo los extremos del período («subió de 1.89 a 1.97») y no refleja el pico intermedio. En la serie `PN01273PM` el máximo fue 8.81 % en 2022-06; la forma completa se ve en el gráfico.
- **Estimaciones sin errores estándar.** Las cifras de pobreza son estimaciones puntuales; no se calculan errores estándar ni intervalos de confianza, aunque la muestra es compleja. Por eso no se afirma que una diferencia pequeña sea «significativa».
- **Diferencia de universo entre método oficial y por personas.** El método oficial del INEI trabaja con hogares (`factor07 × mieperho`) y el cálculo por personas usa los residentes habituales con `facpob07`. La pobreza nacional sale 27.58 % con el primero y 27.53 % con el segundo (rural: 39.30 % y 39.44 %). No es un error del factor: el universo es otro. Área y departamento usan el método oficial; sexo, el de personas, y el gráfico lo rotula.
- **Plugins en el modo B.** La ejecución de la Parte 3 (informe final) se hizo con los plugins del usuario cargados. La evaluación usa `--setting-sources project,local`, es decir, solo las skills y los ajustes del proyecto. Las respuestas de la Parte 3 usaron únicamente `mcp__bcrp` y las tres Skills, pero el entorno no era idéntico.
- **Fuentes no comparables entre sí.** La inflación es mensual y de Lima Metropolitana; la pobreza es anual (2024) y por área o departamento. El departamento Lima (15) no es Lima Metropolitana y excluye al Callao (07).
- **Descarga del INEI.** Puede bloquear la descarga automática; en ese caso hay que bajar los zip a mano (sección 5).
- **Datos revisables.** El BCRP puede revisar sus series después de la consulta.

## 11. Ejemplo de ejecución completa

La Parte 3 se ejecutó en una sola sesión de `claude -p`, desde `tarea_4/`, con el prompt de `evidencias_ia/integracion/prompt_ejecucion.txt`:

```
claude -p "$(cat evidencias_ia/integracion/prompt_ejecucion.txt)" --output-format stream-json --verbose \
  --mcp-config .mcp.json --strict-mcp-config --no-session-persistence \
  --allowedTools "Skill" "Read" "Bash(uv run:*)" "mcp__bcrp" "ReadMcpResourceTool" > registro_crudo.jsonl
uv run informes/sanear_registro.py registro_crudo.jsonl evidencias_ia/integracion/ejecucion.jsonl
```

Antes de ejecutarla se borró `salidas/personas_2024.parquet`. El agente hizo 16 llamadas a herramientas, con 5 herramientas MCP y 3 Skills distintas:

1. Con `bcrp`: `buscar_series`, la ficha `bcrp://serie/PN01273PM`, `resumen`, `serie` y `graficar_serie` para 2020-01 a 2024-12.
2. Con las Skills: como faltaba la base procesada, ejecutó `limpiando-enaho` (16 verificaciones aprobadas, 0 fallidas) y luego `graficando-enaho` y `mapeando-enaho`.

Hallazgos principales del informe:

- La inflación a 12 meses de Lima Metropolitana (`PN01273PM`) subió hasta 8.81 % en 2022-06 y terminó el período en 1.97 % (2024-12).
- En 2024 la pobreza monetaria rural (39.3 %) superó a la urbana (24.8 %) en 14.5 puntos porcentuales, y entre departamentos fue de 6.0 % en Ica a 45.0 % en Cajamarca.

Resultado: gráfico de la serie del BCRP, gráficos de pobreza por área y por departamento, y el mapa departamental. El informe resultante está en `informes/informe_final.md` y sus cifras, en `informes/trazabilidad.md`.

## 12. Evidencias de IA (`evidencias_ia/`)

| Carpeta | Contenido |
|---|---|
| `mcp/` | Sesiones de Claude Code de las fases 0, 1a y 1b (servidor MCP) |
| `skills/` | Sesiones de las fases 2a y 2b (desarrollo de las tres Skills) |
| `integracion/` | Prompt, comando y registro saneado (`ejecucion.jsonl`) de la ejecución completa |
| `evaluacion/` | Registros `.jsonl` de cada pregunta y modo de la evaluación |

Verificación manual: la estudiante comprobó 6 afirmaciones del informe por su cuenta contra el BCRP (serie `PN01273PM`) y la presentación del jefe del INEI. Está en [`informes/verificacion.md`](informes/verificacion.md).

Los registros se sanean con `informes/sanear_registro.py` antes de guardarse (oculta rutas personales y posibles credenciales).

## 13. Innovaciones

- **Verificación automática de cifras.** `informes/generar_trazabilidad.py` arma `informes/trazabilidad.md` con las cifras que salen de las respuestas de las herramientas (`ejecucion.jsonl`) y de los archivos de la ENAHO. Además hace una verificación independiente: consulta la API del BCRP sin pasar por el MCP y recalcula la pobreza desde los microdatos. `informes/verificar_informe.py` falla si el informe contiene un número que no está en la trazabilidad; hoy comprueba 211 números. Se probó en negativo con una copia del informe a la que se le inyectaron tres cifras (31.77, -0.55 y 39.4): el verificador falló con código 1 y señaló las tres (registrado en `evidencias_ia/skills/04_skills_2a_2b.md`).
- **Detección de inconsistencias entre herramientas.** `mapeando-enaho` compara los 25 departamentos con la referencia de la sesión 16 (tolerancia de 0.05 pp por el redondeo de la referencia). Si alguno se desvía, el script termina con error y no guarda el mapa.
- **Pruebas de robustez.** `mcp/test_server.py` tiene 12 pruebas: las 10 requeridas (8 originales y 2 sobre `graficar_serie`) y 2 propias, una para un período sin datos (2030), que da un error claro, y otra para una búsqueda sin resultados, que devuelve una lista vacía.
- **Doble método de estimación, rotulado.** La pobreza se calcula con el método oficial del INEI (hogares, `factor07 × mieperho`) y, de forma informativa, por personas (`facpob07`). `indicadores.csv` rotula el método de cada fila, y la diferencia de universo se explica en `limpiando-enaho/reference.md` y en la sección 10.
- **Robustez ante fallos del BCRP.** El servidor usa caché en memoria y en disco, pausa entre pedidos, hasta 6 reintentos con espera creciente y errores explícitos; nunca rellena ni inventa datos.
- **Análisis al desactivar herramientas.** El experimento A/B de la Parte 4 compara 10 preguntas sin herramientas (modo A) y con MCP y Skills (modo B); los resultados están en la sección 9 y en `evaluacion/comparacion.md`.

No se implementó ningún dashboard de resultados.
