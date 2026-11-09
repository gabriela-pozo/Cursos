# Mejoras pendientes

Mejoras para reutilizar el proyecto con otros años, otras fuentes y otras encuestas. **La 2 (título de `graficar_serie`) ya está implementada (commit `acb310c`); las demás siguen pendientes.** Las estimaciones de esfuerzo son aproximadas y suponen una persona que conoce el código.

## 1. Parametrizar el año en las Skills

- **Problema.** El año 2024 está fijo en el código. En `limpiando-enaho/scripts/limpiar.py` hay una constante `ANIO = 2024`, pero las cifras de referencia de la validación también son de 2024 (`REF_POBREZA`, `REF_URBANA`, `REF_RURAL`, `REF_RESIDENTES`, `REF_HOGARES`). `graficar.py` y `mapear.py` repiten «2024» en rutas (`personas_2024.parquet`), títulos y fuentes, y `mapear.py` compara con una referencia de 2024 de la sesión 16. `datos/descargar.py` descarga solo los módulos 966 (código INEI del 2024). Las Skills ya avisan que sus validaciones son solo de 2024.
- **Archivos que tocaría.** `.claude/skills/*/scripts/*.py` (los tres), `datos/descargar.py`, los `SKILL.md` y la referencia de `mapeando-enaho/referencias/`.
- **Cómo.** Recibir `--anio` por línea de comandos; leer las referencias de un CSV por año en lugar de constantes; si un año no tiene referencia, marcar la verificación como `OMITIDA` y decirlo, no aprobarla.
- **Esfuerzo.** Medio: 1 a 2 días. El grueso es conseguir y validar las cifras oficiales de cada año nuevo, no el código.

## 2. Corregir el título de `graficar_serie` (implementada)

- **Estado.** Implementada en el commit `acb310c`: el título ahora incluye el máximo y el mínimo con su período. La Figura 1 del informe no se regeneró y conserva el título antiguo. Lo que sigue describe el problema original.

- **Problema.** El título automático describe solo el primer y el último dato («subió de 1.89 a 1.97») y no refleja el pico intermedio. Para `PN01273PM`, el máximo fue 8.81 % en 2022-06. El informe ya lo declara como limitación.
- **Archivo que tocaría.** `mcp/server.py`, función `graficar_serie` (donde se calcula `verbo` y `titulo`), y su prueba en `mcp/test_server.py`.
- **Cómo.** Elegir el título según la forma de la serie: si el máximo o el mínimo no están en los extremos, mencionarlos («subió hasta X en P y terminó en Y»). Reutilizar `maximo` y `minimo`, que ya se calculan en esa función.
- **Esfuerzo.** Bajo: unas 2 horas, con una prueba nueva.

## 3. Errores estándar con el diseño muestral

- **Problema.** Las pobrezas son estimaciones puntuales, sin errores estándar ni intervalos de confianza. Por eso no se puede decir si una diferencia pequeña (por ejemplo, entre sexos o entre departamentos cercanos) es distinguible del azar. La ENAHO tiene muestra compleja, con conglomerados y estratos.
- **Archivos que tocaría.** `limpiando-enaho/scripts/limpiar.py`: habría que conservar y validar en el parquet las variables del diseño (conglomerado, estrato y factor de expansión). También `indicadores.csv` (columnas de error estándar e intervalo), `graficar.py` (barras de error), `reference.md` y los `SKILL.md`.
- **Cómo.** Estimar la varianza con un método de diseño complejo (linealización de Taylor o réplicas) y verificar con las cifras publicadas por el INEI.
- **Esfuerzo.** Alto: 3 a 5 días. Falta decidir el método y la biblioteca, y validar los resultados contra una fuente oficial.

## 4. Un segundo MCP con otra fuente oficial

- **Problema.** El agente solo consulta el BCRP. La pregunta de investigación junta una serie del BCRP con una encuesta del INEI, pero esta última entra por Skills y archivos, no por una herramienta consultable.
- **Archivos que tocaría.** Un servidor nuevo (por ejemplo, `mcp/server_inei.py`), su entrada en `.mcp.json` y pruebas en un archivo aparte, para no tocar `mcp/test_server.py`.
- **Cómo.** Reutilizar el patrón de `mcp/server.py`: catálogo local, validación de código, caché, reintentos y `ToolError` explícito. La fuente concreta (INEI, MEF u otra) y su acceso programático están por definir.
- **Esfuerzo.** Alto: 3 a 5 días, según lo que ofrezca la fuente.

## 5. Funciones reutilizables para otras encuestas del INEI

- **Problema.** `limpiar.py` mezcla lógica general (leer `.dta` con llaves como texto, unir con `validate="m:1"`, validar y escribir `validacion.txt`) con reglas propias de la ENAHO 2024. La clase `Falla` se repite en los tres scripts, y `procesar` tiene unas 175 líneas.
- **Archivos que tocaría.** Los tres scripts de `.claude/skills/*/scripts/`; el módulo común podría vivir en una carpeta aparte, por ejemplo `lib/`. Hay que revisar cómo lo resuelve `uv run` en cada Skill.
- **Cómo.** Extraer: lectura con llaves (`leer`, `buscar_dta`, `normalizar`), la clase `Verificaciones`, el cálculo ponderado (`tasa_pobreza`) y el lienzo de los gráficos. Dejar en la configuración de cada encuesta las llaves, los módulos y las referencias.
- **Esfuerzo.** Medio a alto: 2 a 4 días, más la corrida de las verificaciones existentes para comprobar que los resultados no cambian (16 aprobadas y las mismas cifras).

## Orden sugerido

1. ~~Título de `graficar_serie`~~ (ya implementada).
2. Parametrizar el año.
3. Funciones reutilizables.
4. Errores estándar.
5. Segundo MCP.
