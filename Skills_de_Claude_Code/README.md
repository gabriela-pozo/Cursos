# Skills de Claude Code para la ENAHO 2024

Tres skills de proyecto en `.claude/skills/` que limpian, grafican y mapean la pobreza monetaria de la ENAHO 2024 (INEI).

| Skill | Entra | Sale |
|---|---|---|
| `limpiando-enaho` | `datos/966-Modulo34.zip`, `datos/966-Modulo02.zip` | `salidas/personas_2024.parquet`, `salidas/validacion.txt` |
| `graficando-enaho` | La base limpia + `area`, `sexo` o `edad` | `figuras/pobreza_<x>_2024.png` |
| `mapeando-enaho` | La base limpia + GeoJSON departamental | `mapas/pobreza_departamento.png` |

`graficando-enaho` y `mapeando-enaho` llaman primero a `limpiando-enaho` si falta la base limpia, así que un solo pedido activa dos skills seguidas.

## 1. Bajar los datos

Desde el navegador (o con `curl -L -O`), a la carpeta `datos/` (no se sube a git):

- Módulo 34, sumaria: https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
- Módulo 02, miembros: https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
- Límites (opcional, `mapear.py` lo baja si falta): https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson

## 2. Correr todo

```bash
uv sync
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run .claude/skills/graficando-enaho/scripts/graficar.py area   # también: sexo, edad
uv run .claude/skills/mapeando-enaho/scripts/mapear.py
```

O desde Claude Code, en esta carpeta: «Haz un mapa de la pobreza por departamento con la ENAHO 2024».

## 3. Validación

`salidas/validacion.txt`: 33,691 hogares, 108,664 residentes habituales, unión m:1 sin pérdidas, pobreza nacional
27.53 % con personas y `facpob07` (27.58 % con la sumaria; INEI: 27.6 %), urbano 24.7 % y rural 39.4 %.

## 4. Evaluación con y sin skills

`pwsh eval_logs/correr.ps1` corre los tres pedidos con `claude -p` con y sin skills (`--disallowedTools Skill`) y guarda los
logs en `eval_logs/`. Los resultados están en `evaluacion.md`.
