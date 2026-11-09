---
name: limpiando-enaho
description: Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO 2024 del INEI y arma la base de personas con pobreza monetaria, departamento, área urbano/rural, sexo y factores de expansión, validada contra las cifras oficiales. Úsala cuando pidan limpiar, procesar, unir o preparar la ENAHO, calcular la pobreza (nacional, urbana, rural, por departamento o por sexo) o cuando falte salidas/personas_2024.parquet para graficar o mapear.
---
# Limpiar la ENAHO 2024

Esta skill es la base de `graficando-enaho` y `mapeando-enaho`. Todo lo que no admite discusión (llaves, filtro, unión,
ponderación, validación) está en el script; tú solo lo ejecutas y lees el resultado. No repitas esos cálculos a mano.

## Pasos

1. Comprueba que existen los microdatos en `datos/` (carpetas `966-Modulo34` y `966-Modulo02`). Si faltan, descárgalos
   con `uv run datos/descargar.py` (son datos públicos del INEI, unos 22 MB) y, si la descarga falla, di exactamente
   qué falló: no inventes datos. El INEI puede bloquear la descarga automática; en ese caso pide al usuario bajar los zip a mano.
2. Ejecuta, desde cualquier carpeta del proyecto:
   ```
   uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py
   ```
3. Lee `salidas/validacion.txt`. Cada verificación sale como `APROBADA`, `FALLIDA`, `INFO` u `OMITIDA`.
   - Si el script termina con `ERROR` es que falló una verificación esencial: **detente**, muestra qué verificación
     falló y con qué valores, y no la corrijas ni muevas tolerancias. No uses ninguna base anterior.
   - Si terminó bien, confirma al usuario las cifras clave (residentes, pobreza nacional, urbana y rural) tomándolas
     del archivo, no de memoria.
4. Resultados: `salidas/personas_2024.parquet` (una fila por residente habitual), `salidas/indicadores.csv` y
   `salidas/validacion.txt`. El parquet contiene microdatos: está en `.gitignore`, no lo subas.

## Reglas que debes respetar al usar los resultados

- **Nombres de departamento, del diccionario.** El código `ubigeo[:2]` se asocia con su nombre solo mediante
  [referencias/departamentos_ubigeo.csv](referencias/departamentos_ubigeo.csv) (25 códigos, Lima `15` y Callao `07`
  separados). `indicadores.csv` ya trae la columna `nombre_categoria` y el parquet `nombre_departamento`: úsalas y
  nunca deduzcas un nombre de memoria.
- **Siempre ponderado.** Nunca promedios simples: la pobreza sin ponderar sale distinta (el archivo de validación lo muestra).
- **Dos métodos, rotulados** (columna `metodo` de `indicadores.csv`):
  - `hogares_factor07_x_mieperho`: método oficial del INEI y el que reproduce las cifras de referencia. Úsalo para
    pobreza nacional, urbana/rural y por departamento.
  - `personas_facpob07`: residentes habituales con su factor de persona. Úsalo para atributos de la persona (sexo,
    edad). Difiere unas décimas del anterior porque el universo es otro; dilo si presentas ambos.
- **Asociaciones, no causas.** Si comparas grupos (urbano/rural, sexo, departamentos), describe diferencias; no afirmes
  que un factor causa la pobreza.
- Si el usuario pide otro año, avisa: las validaciones y referencias de esta skill son solo de 2024.

Para decisiones de la base (qué sumaria se usa y por qué, definición de cada variable, universos y limitaciones) lee
[reference.md](reference.md) antes de usar una variable que no aparece en el parquet.
