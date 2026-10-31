# Diccionario de datos

## `data/processed/indicadores_distrito.csv` (1,893 filas, una por distrito)

| Columna | Descripción | Fuente |
|---|---|---|
| `codgeo` | Ubigeo de 6 dígitos (vacío en Sangani, distrito nuevo sin colegios en el padrón) | Padrón Minedu |
| `dpto`, `prov`, `dist` | Nombres como aparecen en los tabulados INEI. Lima aparece como `LIMA METROPOLITANA` y `REGIÓN LIMA`; Callao sin provincia | INEI |
| `metodo_cruce` | Cómo se asignó el ubigeo: `exacto`, `sin_provincia`, `aprox_provincia`, `sin_padron` | Propio |
| `pob_total` | Suma de edades simples (≈ población censada) | INEI cuadro 2 |
| `pob_0_5`, `pob_6_11`, `pob_12_16`, `pob_60mas` | Población por grupo de edad | INEI cuadro 2 |
| `edad_0` … `edad_11` | Población por edad simple | INEI cuadro 2 |
| `pct_rural` | Proporción de población rural | INEI cuadro 2 |
| `irc_central` | (población 3–5) ÷ (población 9–11) | Propio |
| `irc_lo`, `irc_hi` | Intervalo de Wilson al 95 % transformado a razón | Propio |
| `irc_tope` | (población 0–5) ÷ (población 6–11), con corrección de omisión de `config.json` | Propio |
| `tipologia` | `contraccion` (IC superior < 0.9), `expansion` (IC inferior > 1), `estable_o_incierto`, `muestra_pequena` (< 150 niños de 9–11) | Propio |
| `asist_3_5` … `asist_17_24` | Proporción que asiste a una institución educativa, por grupo de edad normativa | INEI Educación cuadro 7 |
| `n_ie`, `alumnos`, `docentes`, `secciones` | Instituciones educativas activas y sus totales | Padrón Minedu |
| `alu_por_docente`, `alu_por_seccion` | Cocientes | Propio |
| `ie_peq` | Colegios con 20 alumnos o menos (incluye programas no escolarizados) | Padrón Minedu |
| `alu_primaria`, `alu_inicial` | Alumnos por nivel | Padrón Minedu |
| `pct_lengua_indigena` | Proporción de la población de 3 y más años que aprendió a hablar en quechua, aimara u otra lengua indígena (suma de las filas indígenas del cuadro) | INEI Educación cuadro 2 |
| `estudia_fuera_5_14` | Proporción de los niños de 5 a 14 años que asisten a un colegio ubicado en otro distrito (vacío si hay menos de 150 niños) | INEI Educación cuadro 8 |
| `indice_envejecimiento` | Población de 60+ por cada 100 menores de 15 años | INEI cuadro 2 |

## `data/processed/padron_distrito.csv`
Agregado por distrito del `Padron.dbf` (solo instituciones activas): colegios, alumnos, docentes, secciones, públicos, rurales, pequeños y por nivel. No contiene datos personales.

## `data/processed/ugel_distrito.csv`
UGEL de cada distrito (`codgeo`, `cod_ugel`, `ugel`). Un distrito puede tener colegios de varias UGEL: se toma la que concentra más alumnos y se guarda cuántas hay (`n_ugel`) y qué parte de los alumnos tiene la elegida (`pct_alumnos_ugel`). Lo escribe `scripts/02b_ugel.py`.

## `data/processed/lengua_distrito.csv`, `flujo_distrito.csv`
Extractos de los cuadros 2 y 8 de Educación (INEI), por distrito. Los escribe `scripts/01c_parse_lengua_flujos.py`.

## `data/processed/crosswalk.csv`
Equivalencia entre el nombre del distrito en INEI y su ubigeo, con método y puntaje, para auditar los casos aproximados (`ANCO-HUALLO`, `SAN FRANCISCO DE RIVACAYCO`, `SANTA CRUZ DE TOLED`, `RAIMONDI`).

## `data/processed/edades_distrito.csv`, `asistencia_distrito.csv`
Extractos directos de los tabulados INEI en formato largo (una fila por distrito y edad o grupo).

## `data/processed/prioridad_distrito.csv` (1,798 filas: distritos con 500 habitantes o más y al menos 2 dimensiones)

Lo escribe `scripts/04b_prioridad.py`. Responde la pregunta B: qué distritos atender primero.

| Columna | Descripción |
|---|---|
| `codgeo`, `dpto`, `prov`, `dist` | Identificación del distrito |
| `pob_total`, `pct_rural` | Copiados de `indicadores_distrito.csv` |
| `demanda` | Percentil (0–100) del IRC central; con `demanda_direccion = "crece"`, IRC alto = percentil alto |
| `cobertura` | Promedio de los percentiles de (1 − asistencia 3–5) y (1 − asistencia 17–24) |
| `condiciones` | Promedio de los percentiles de alumnos por docente y (1 − uso de internet de 5 a 14 años) |
| `n_dim` | Número de dimensiones con dato (2 o 3) |
| `indice` | Promedio ponderado de las dimensiones disponibles, con los pesos de `config.json` (las dimensiones se redondean a 1 decimal antes de promediar) |
| `omision_pct` | Omisión censal estimada del distrito |
| `rank` | Puesto de mayor a menor índice; los empates se ordenan por ubigeo |

Percentil = (n.º de distritos con valor menor + 0.5 × n.º con valor igual) ÷ n × 100. 100 es la situación más exigida.

## `web/data/distritos.js` (`window.DISTRITOS`, 1,893 objetos)

Lo escribe `scripts/05_build_web.py` uniendo `indicadores_distrito.csv` con `prioridad_distrito.csv`.

| Campo | Descripción |
|---|---|
| `id`, `n`, `pv`, `d`, `amb` | Ubigeo, distrito, provincia, departamento (Lima y Callao unificados) y ámbito INEI original |
| `pop`, `k611`, `p60`, `e` | Población total, de 6 a 11 años, de 60 o más, y por edad simple de 0 a 11 años |
| `rur`, `a35`, `a1216`, `a1724` | Proporción rural y asistencia escolar por grupo de edad |
| `ie`, `peq`, `alu`, `doc`, `apd`, `env` | Colegios, colegios de 20 alumnos o menos, alumnos, docentes, alumnos por docente, índice de envejecimiento |
| `irc`, `tipologia` | IRC central y tipología de cohortes |
| `omision`, `internet` | Omisión censal y uso de internet de 5 a 14 años |
| `lengua`, `fuera` | Proporción con lengua materna indígena y proporción de niños de 5 a 14 años que estudia en otro distrito |
| `ug`, `uc` | Nombre y código de la UGEL |
| `demanda`, `cobertura`, `condiciones`, `n_dim`, `indice`, `rank` | Columnas de `prioridad_distrito.csv`; `null` si el distrito no tiene índice |

## `web/data/geometria.js` (`window.GEO`)
Polígonos simplificados (1,824 distritos), con coordenadas redondeadas a 3 decimales.

## `web/data/findings.js` (`window.FINDINGS`) y `docs/hallazgos.md`

Los escribe `scripts/05b_findings.py`. Son la única fuente de las cifras que aparecen en los textos del dashboard, del README y de las publicaciones.

| Clave | Contenido |
|---|---|
| `kpis` | Distritos evaluados, distritos de prioridad alta y umbral, niños de 3–5 por cada 100 de 9–11, cobertura de 3–5, alumnos por docente, niños de 3–5 en distritos de prioridad alta |
| `top15` | Los 15 primeros del ranking, con sus tres dimensiones |
| `hallazgos`, `frases` | Textos con las cifras ya calculadas |
| `tipologia` | Distritos por tipología de cohortes |
| `conteos` | Sin polígono, omisión mayor al umbral, sin índice, con tres dimensiones |
| `detalle` | Medianas y conteos que respaldan cada hallazgo |
