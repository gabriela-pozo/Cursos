# Variables de `salidas/personas_2024.parquet`

| Variable | Origen | Significado |
|---|---|---|
| conglome, vivienda, hogar, codperso | 02 | Llaves (texto) |
| ubigeo, departamento | 34 | Ubigeo de 6 dígitos; `departamento = ubigeo[:2]` (01 Amazonas … 15 Lima, 07 Callao … 25 Ucayali) |
| dominio | 34 | 1–7 costa/sierra/selva norte, centro, sur; 8 = Lima Metropolitana |
| estrato | 34 | 1–8; `urbano = estrato <= 5` |
| pobreza | 34 | 1 pobre extremo, 2 pobre no extremo, 3 no pobre; `pobre = pobreza <= 2` |
| mieperho, factor07 | 34 | Miembros del hogar y factor de hogar |
| p204, p205, p206 | 02 | Filtro de residentes habituales: `(p204==1 & p205==2) | (p204==2 & p206==1)` |
| p207, mujer | 02 | Sexo (1 hombre, 2 mujer) |
| p208a, edad | 02 | Edad en años |
| facpob07 | 02 | Factor de expansión de personas: úsalo siempre |

Otras variables (educación, salud, empleo) están en otros módulos (03, 04, 05): pide al usuario el zip y únelas por las llaves.
