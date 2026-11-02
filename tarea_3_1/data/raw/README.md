# Datos de entrada (no se suben al repositorio)

Coloca aquí los archivos descargados:

1. **INEI, tabulados del Censo 2025** (Excel): `inei_tabulados/{código}_Educacion.xlsx` y `inei_tabulados/{código}_Indicadores_demograficos.xlsx`, para el código `00` (nacional) y `01` a `27` (los departamentos; Lima se publica como `26` Región Lima y `27` Lima Metropolitana, y no existe el `15`).
   Patrón de descarga:
   `https://proyectos.inei.gob.pe/dir-segmentacion-ci/postcensal/prod/adjuntos/censos-2025/descarga_datos/tabulados/{código}/poblacion/{Educacion|Indicadores_demograficos}.xlsx`
2. **Minedu, Censo Educativo 2025** (ESCALE → Bases de datos → A. Censo Educativo → 2025): `Padron.dbf`. Contiene nombres de directores y teléfonos de las instituciones: no lo publiques.
3. **Polígonos distritales**: `peru_distrital_simple.geojson` de https://github.com/juaneladio/peru-geojson (licencia MPL-2.0).
