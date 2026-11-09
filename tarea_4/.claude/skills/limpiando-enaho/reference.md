# Referencia técnica · limpiando-enaho

Documenta las decisiones del script `scripts/limpiar.py`. Las cifras de cada corrida no se copian aquí: están en
`salidas/validacion.txt` y `salidas/indicadores.csv`, que el script genera desde los microdatos.

## Archivos de entrada

Los zip del INEI se extraen en carpetas anidadas (`datos/966-Modulo34/966-Modulo34/...`), por eso el script busca
por nombre dentro de `datos/` y no por ruta fija.

| Módulo | Archivo usado | Una fila por | Llaves | Factor |
|---|---|---|---|---|
| 34 (sumaria) | `sumaria-2024.dta` | hogar | `conglome`, `vivienda`, `hogar` | `factor07` (hogar), `mieperho` (miembros) |
| 02 (miembros) | `enaho01-2024-200.dta` | persona | las tres + `codperso` | `facpob07` |

El módulo 02 trae además dos tablas de códigos (`enaho_tabla_ciuo_88.dta`, `enaho_tabla_cno_2015.dta`) que no se usan.

## Qué sumaria usar: decisión con datos

El módulo 34 trae dos archivos: `sumaria-2024.dta` (163 variables) y `sumaria-2024-12g.dta` (242 variables). Se
comparó con los datos, no por costumbre, y el propio script repite la comparación en cada corrida (última verificación de
`validacion.txt`):

- Ambas tienen el **mismo número de hogares** (el de la sesión 16) y exactamente los **mismos hogares** por llaves.
- Son **idénticas en todas las variables que definen la pobreza**: `pobreza`, `pobrezav`, `factor07`, `mieperho`,
  `ubigeo`, `estrato`, `dominio`, `gashog2d`, `linea` y `linpe`. Por eso el recuento de hogares y la pobreza **no
  sirven para desempatar**: dan lo mismo con cualquiera.
- Solo difieren en las columnas de gasto por grupos (`gru*hd`): la 12g agrega el desglose del gasto en 12 grupos.

**Decisión: `sumaria-2024.dta`.** Es la sumaria estándar, tiene todo lo que este proyecto necesita y es la que usa la
sesión 16. La 12g solo agregaría columnas de gasto que no se usan. Si en el futuro hiciera falta el gasto por grupos,
la unión por las tres llaves permite incorporarla sin cambiar los indicadores de pobreza.

## Pipeline

1. **Lectura:** `pd.read_stata(..., convert_categoricals=False)`. Las llaves llegan como texto y se verifica que cada
   una tenga un largo único; si llegaran como número el script se detiene, porque ya se habrían perdido los ceros.
2. **Nombres:** todo a minúscula. La columna del año llega como `aÑo` y queda como `anio`.
3. **Residentes habituales:** `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`. Los nulos cuentan como
   «no cumple». Es la condición del issue y de la sesión 16.
4. **Unión:** `residentes.merge(sumaria, on=[conglome, vivienda, hogar], validate="m:1")`. Muchas personas por hogar;
   si hubiera hogares repetidos, pandas lanza error y el script se detiene. Además se verifica que no se pierda ni
   duplique ninguna persona y que `ubigeo` y `estrato` coincidan entre persona y hogar.
5. **Variables nuevas:** `departamento = ubigeo[:2]`; `urbano = estrato <= 5` (el resto es rural); `pobre = pobreza <= 2`
   (1 = pobre extremo, 2 = pobre no extremo, 3 = no pobre); `sexo` desde `p207` (1 = Hombre, 2 = Mujer); `edad` desde `p208a`.
6. **Validación** y escritura de resultados (ver abajo). El diccionario de cada variable está en
   `datos/966-Modulo34/966-Modulo34/Diccionario2024.pdf` y `datos/966-Modulo02/966-Modulo02/Diccionario2024.pdf`.

## Ponderación: dos universos, dos métodos

- **Método oficial del INEI (hogares):** la pobreza se mide en el hogar. Se pondera cada hogar con `factor07 × mieperho`
  (personas que representa). Reproduce las cifras de referencia (27.6 % nacional, 24.8 % urbana, 39.3 % rural).
  Es la validación esencial.
- **Personas residentes (`facpob07`):** el universo es el de los residentes habituales del módulo 02, que es más
  chico que el total de miembros de hogar de la sumaria. Por eso da unas décimas distinto (la mayor diferencia aparece
  en el área rural). **No es un error del factor**: ponderar a los residentes con `factor07` o con `facpob07` da lo
  mismo; lo que cambia es a quién se cuenta. Se informa en `validacion.txt` con su diferencia, sin ocultarla.
- Para atributos de la persona (sexo, edad) solo existe el método por personas.
- Los totales de «población expandida» de `indicadores.csv` son la suma de los factores de cada universo.

Nunca se usa el promedio simple: `validacion.txt` muestra, solo como contraste, cuánto se alejaría.

## Verificaciones y qué pasa si fallan

Esenciales (si una falla, el script termina con `ERROR`, borra `personas_2024.parquet` e `indicadores.csv` previos y
**no ajusta nada**): llaves con ceros, hogares únicos y su número, personas únicas, residentes habituales, unión m:1
sin pérdidas ni duplicados, coincidencia persona-hogar, los 25 códigos territoriales, factores presentes y positivos,
valores válidos de `pobreza` y `sexo`, y pobreza nacional, urbana y rural por el método oficial (tolerancia ± 0.1 pp,
declarada antes de ver los resultados). No esenciales: las verificaciones `INFO` (método por personas, pobreza sin
ponderar) y la comparación de las dos sumarias.

## Códigos territoriales

`departamento` va de `01` a `25`: Lima (`15`) y Callao (`07`) están separados, como en el GeoJSON departamental
(`FIRST_IDDP`). Se conserva siempre como texto de 2 caracteres.

## Limitaciones

- Son estimaciones puntuales: no se calculan errores estándar ni intervalos de confianza (la muestra es compleja, con
  conglomerados y estratos; las variables están en la base si se quisiera hacerlo).
- Las estimaciones por departamento tienen menos observaciones que las nacionales; `n_muestra` está en `indicadores.csv`.
- Las referencias y validaciones son solo del año 2024.
- Las diferencias entre grupos son descriptivas; no demuestran relaciones de causa.
