---
name: limpiando-enaho
description: Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO del INEI y arma una base de personas con pobreza y factor de expansión. Úsala cuando pidan limpiar, unir o analizar la ENAHO, o calcular la pobreza nacional, por departamento o región (Cusco, Lima, etc.), área, sexo o edad.
argument-hint: [año]
---
# Limpiar la ENAHO

1. Si faltan `datos/966-Modulo34.zip` o `datos/966-Modulo02.zip`, pide al usuario bajarlos del INEI (código 966 = 2024).
2. Si ya existe `salidas/personas_2024.parquet` y `salidas/validacion.txt`, no vuelvas a limpiar. Si no, corre exactamente:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio 2024`
3. Lee `salidas/validacion.txt`. Si la pobreza difiere del INEI en más de 0.1 puntos, detente y avisa.
4. Responde con `salidas/personas_2024.parquet`. Toda cifra va ponderada con `facpob07`:
   `100 * (pobre * facpob07).sum() / facpob07.sum()`. Departamento = `departamento` (código de 2 dígitos, p. ej. Cusco = "08").
5. Antes de usar una variable que no está en la base, lee `reference.md`.
