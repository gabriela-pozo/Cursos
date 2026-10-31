---
name: mapeando-enaho
description: Hace un mapa coroplético de la pobreza de la ENAHO del INEI por departamento del Perú, uniendo por código de ubigeo. Úsala cuando pidan un mapa de la pobreza por departamento o región.
---
# Mapear la ENAHO

1. Si no existe `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho`.
2. Corre `uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py` (baja el GeoJSON a `datos/` si falta).
3. Responde con el mayor y el menor departamento y la ruta `mapas/pobreza_departamento.png`.

Reglas (el script ya las cumple):
- Une por código: `ubigeo[:2]` con `FIRST_IDDP`, como texto de 2 dígitos. Nunca por nombre: «APURIMAC» no es «Apurímac».
- Exige 25 departamentos y ninguno sin dato. Lima (15) y Callao (07) van separados.
- Un color de claro a oscuro desde 0 (Reds); nunca arcoíris. Leyenda con la unidad: % de personas.
