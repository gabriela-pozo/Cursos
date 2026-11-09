"""Limpia la ENAHO 2024 (módulos 34 y 02) y arma la base de personas con pobreza y factores de expansión.

    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py

Pasos, siempre en este orden:
  1. Leer los .dta (se buscan dentro de datos/, aunque estén en carpetas anidadas) con convert_categoricals=False
     y las llaves como texto, para no perder los ceros iniciales.
  2. Normalizar los nombres de columna a minúscula («aÑo» pasa a «anio»).
  3. Filtrar residentes habituales: ((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1)).
  4. Unir personas con hogares por conglome, vivienda y hogar con merge(validate="m:1").
  5. Construir departamento (ubigeo[:2]), área urbano/rural (estrato <= 5), pobre (pobreza <= 2) y sexo.
  6. Validar todo y escribir salidas/validacion.txt con cada verificación APROBADA o FALLIDA.
  7. Si NINGUNA verificación esencial falló, guardar salidas/personas_2024.parquet y salidas/indicadores.csv.

Si una verificación esencial falla el script termina con error y NO ajusta nada para que coincida con la referencia:
borra los resultados anteriores (para que nadie use una base inválida) y deja validacion.txt con lo ocurrido.
Toda cifra sale del procesamiento de los microdatos; las únicas constantes son los valores de referencia del issue.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ANIO = 2024
LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]
SUMARIA = f"sumaria-{ANIO}.dta"              # la elegida: ver reference.md, sección «Qué sumaria usar»
SUMARIA_12G = f"sumaria-{ANIO}-12g.dta"      # solo se usa para comprobar que la elección no cambia la pobreza
MIEMBROS = f"enaho01-{ANIO}-200.dta"
DEPARTAMENTOS = {f"{i:02d}" for i in range(1, 26)}

# Valores de referencia (issue #201 y sesión 16). Son metas contra las que se valida, nunca resultados.
REF_POBREZA, REF_URBANA, REF_RURAL, TOLERANCIA_PP = 27.6, 24.8, 39.3, 0.1
REF_RESIDENTES, REF_HOGARES = 108_664, 33_691


class Falla(Exception):
    """Error explícito que detiene el proceso."""


# --------------------------------------------------------------------------------------------- lectura
def buscar_dta(datos: Path, nombre: str, obligatorio: bool = True) -> Path | None:
    """Busca nombre dentro de datos/ y sus subcarpetas (los zip del INEI se extraen en carpetas anidadas)."""
    hallados = sorted(p for p in datos.rglob("*") if p.is_file() and p.name.lower() == nombre.lower())
    if hallados:
        return hallados[0]
    if obligatorio:
        raise Falla(f"No encontré {nombre} dentro de {datos}. Descárguelo con: uv run datos/descargar.py")
    return None


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Nombres de columna en minúscula; la columna del año llega como «aÑo» y pasa a «anio»."""
    df.columns = [c.lower() for c in df.columns]
    return df.rename(columns={"año": "anio"})


def leer(ruta: Path, llaves: list[str], columnas: list[str] | None = None) -> pd.DataFrame:
    """Lee un .dta sin convertir categorías y comprueba que las llaves son texto (así conservan sus ceros)."""
    df = normalizar(pd.read_stata(ruta, convert_categoricals=False, columns=columnas))
    for k in llaves:
        if k not in df.columns:
            raise Falla(f"{ruta.name} no trae la llave {k!r}.")
        if not pd.api.types.is_string_dtype(df[k]):
            raise Falla(f"{ruta.name}: la llave {k!r} llegó como {df[k].dtype}, no como texto: se habrían perdido ceros.")
        df[k] = df[k].astype(str).str.strip()
    return df


# --------------------------------------------------------------------------------------------- estimaciones
def tasa_pobreza(df: pd.DataFrame, peso: str, mascara=None) -> float:
    """% de pobres ponderado: suma de pesos de los pobres / suma de pesos de todos (nunca un promedio simple)."""
    d = df if mascara is None else df[mascara]
    return float(100 * d.loc[d["pobre"], peso].sum() / d[peso].sum())


class Verificaciones:
    """Lista de comprobaciones con su resultado, para escribir validacion.txt."""

    def __init__(self):
        self.filas = []

    def agregar(self, nombre: str, estado: str, obtenido: str, esperado: str = "", esencial: bool = True):
        self.filas.append({"nombre": nombre, "estado": estado, "obtenido": obtenido, "esperado": esperado,
                           "esencial": esencial})

    def comprobar(self, nombre: str, ok: bool, obtenido: str, esperado: str = "", esencial: bool = True):
        self.agregar(nombre, "APROBADA" if ok else "FALLIDA", obtenido, esperado, esencial)

    def esenciales_fallidas(self):
        return [f for f in self.filas if f["estado"] == "FALLIDA" and f["esencial"]]


# --------------------------------------------------------------------------------------------- proceso
def procesar(raiz: Path, datos: Path, salidas: Path) -> None:
    v = Verificaciones()
    ruta_sum, ruta_mie = buscar_dta(datos, SUMARIA), buscar_dta(datos, MIEMBROS)
    ruta_12g = buscar_dta(datos, SUMARIA_12G, obligatorio=False)
    rel = lambda p: p.relative_to(raiz).as_posix() if p.is_relative_to(raiz) else str(p)  # noqa: E731

    # 1-2. Leer y normalizar
    hogares = leer(ruta_sum, LLAVES_HOGAR)
    personas = leer(ruta_mie, LLAVES_PERSONA)

    # Llaves: texto con su largo completo (si se hubieran leído como número, habrían perdido ceros)
    largos = {k: sorted(set(df[k].str.len())) for df, ks in ((hogares, LLAVES_HOGAR), (personas, LLAVES_PERSONA)) for k in ks}
    v.comprobar("Llaves leídas como texto con ceros iniciales (largo único por llave)",
                all(len(x) == 1 for x in largos.values()),
                ", ".join(f"{k}: {x}" for k, x in largos.items()), "un solo largo por llave")

    # Unicidad antes de unir
    v.comprobar("Sumaria: una fila por hogar (sin llaves duplicadas)", not hogares.duplicated(LLAVES_HOGAR).any(),
                f"{len(hogares):,} hogares", f"{REF_HOGARES:,} hogares y sin duplicados")
    v.comprobar("Sumaria: número de hogares", len(hogares) == REF_HOGARES, f"{len(hogares):,}", f"{REF_HOGARES:,}")
    v.comprobar("Miembros: una fila por persona (sin llaves duplicadas)", not personas.duplicated(LLAVES_PERSONA).any(),
                f"{len(personas):,} filas", "sin duplicados")

    # 3. Residentes habituales
    p204, p205, p206 = personas["p204"], personas["p205"], personas["p206"]
    es_residente = ((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))
    residentes = personas[es_residente].copy()
    v.comprobar("Residentes habituales", len(residentes) == REF_RESIDENTES,
                f"{len(residentes):,} de {len(personas):,} filas", f"{REF_RESIDENTES:,}")

    # 4. Unión personas -> hogares (muchas personas por hogar)
    cols_hogar = LLAVES_HOGAR + ["ubigeo", "dominio", "estrato", "pobreza", "factor07", "mieperho"]
    try:
        unido = residentes.merge(hogares[cols_hogar], on=LLAVES_HOGAR, how="left", suffixes=("_p", "_h"),
                                 validate="m:1", indicator=True)
    except pd.errors.MergeError as e:
        raise Falla(f"La unión personas-hogares no es m:1 (hay hogares duplicados): {e}") from None
    sin_hogar = int((unido["_merge"] != "both").sum())
    v.comprobar("Unión m:1: no se pierden ni se duplican personas",
                len(unido) == len(residentes) and sin_hogar == 0,
                f"{len(residentes):,} residentes -> {len(unido):,} filas; {sin_hogar} sin hogar",
                "mismas filas que antes de unir y 0 sin hogar")
    v.comprobar("Unión m:1: ninguna persona repetida tras unir", not unido.duplicated(LLAVES_PERSONA).any(),
                f"{int(unido.duplicated(LLAVES_PERSONA).sum())} repetidas", "0")
    dif_ubigeo = int((unido["ubigeo_p"] != unido["ubigeo_h"]).sum())
    dif_estrato = int((unido["estrato_p"] != unido["estrato_h"]).sum())
    v.comprobar("Persona y hogar coinciden en ubigeo y estrato", dif_ubigeo == 0 and dif_estrato == 0,
                f"{dif_ubigeo} ubigeo y {dif_estrato} estrato distintos", "0 y 0")
    unido = unido.drop(columns=["ubigeo_p", "estrato_p", "dominio_p", "_merge"]).rename(
        columns={"ubigeo_h": "ubigeo", "estrato_h": "estrato", "dominio_h": "dominio"})

    # 5. Variables nuevas
    unido["departamento"] = unido["ubigeo"].str[:2]
    unido["urbano"] = unido["estrato"] <= 5
    unido["area"] = np.where(unido["urbano"], "Urbano", "Rural")
    unido["pobre"] = unido["pobreza"] <= 2
    unido["pobre_extremo"] = unido["pobreza"] == 1
    unido["sexo"] = unido["p207"].map({1: "Hombre", 2: "Mujer"})
    unido["edad"] = unido["p208a"]
    for c in ("facpob07", "factor07"):
        unido[c] = unido[c].astype("float64")

    # 6. Validaciones de territorio, pesos y pobreza
    codigos = set(unido["departamento"])
    v.comprobar("25 códigos territoriales (ubigeo[:2]), de 01 a 25", codigos == DEPARTAMENTOS,
                f"{len(codigos)} códigos; faltan {sorted(DEPARTAMENTOS - codigos)}, sobran {sorted(codigos - DEPARTAMENTOS)}",
                "25 códigos, de 01 a 25 (Lima 15 y Callao 07 separados)")
    pesos_ok = bool(unido["facpob07"].notna().all() and (unido["facpob07"] > 0).all()
                    and unido["factor07"].notna().all() and (unido["factor07"] > 0).all())
    v.comprobar("Factores de expansión (facpob07, factor07) presentes y positivos en todas las filas", pesos_ok,
                f"facpob07 nulos: {int(unido['facpob07'].isna().sum())}", "0 nulos y todos > 0")
    v.comprobar("Variable pobreza solo toma los valores 1, 2 y 3 (extremo, no extremo, no pobre)",
                set(unido["pobreza"].unique()) <= {1, 2, 3}, f"valores: {sorted(int(x) for x in unido['pobreza'].unique())}", "{1, 2, 3}")
    v.comprobar("Sexo reconocido en todas las filas (p207 = 1 o 2)", bool(unido["sexo"].notna().all()),
                f"{int(unido['sexo'].isna().sum())} sin sexo", "0")

    # Método OFICIAL del INEI: la pobreza se mide en el hogar (sumaria) y se pondera con factor07 x mieperho.
    # De ahí salen las cifras de referencia (27.6 / 24.8 / 39.3), así que es la validación esencial.
    hog = hogares.assign(pobre=hogares["pobreza"] <= 2, pobre_extremo=hogares["pobreza"] == 1,
                         urbano=hogares["estrato"] <= 5, departamento=hogares["ubigeo"].str[:2],
                         w=hogares["factor07"].astype("float64") * hogares["mieperho"])
    hog["area"] = np.where(hog["urbano"], "Urbano", "Rural")
    nac_h, urb_h, rur_h = (tasa_pobreza(hog, "w"), tasa_pobreza(hog, "w", hog["urbano"]),
                           tasa_pobreza(hog, "w", ~hog["urbano"]))
    for nombre, valor, ref in (("nacional", nac_h, REF_POBREZA), ("urbana (estrato <= 5)", urb_h, REF_URBANA),
                               ("rural (estrato > 5)", rur_h, REF_RURAL)):
        v.comprobar(f"Pobreza monetaria {nombre} · método oficial (hogares, factor07 x mieperho)",
                    abs(valor - ref) <= TOLERANCIA_PP, f"{valor:.2f} %", f"{ref} % ± {TOLERANCIA_PP} pp")

    # Por personas residentes con facpob07: es otro universo (108,664 residentes frente a los miembros de hogar de la
    # sumaria), por eso difiere unas décimas. Se informa con su diferencia; no es una validación esencial.
    nac, urb, rur = (tasa_pobreza(unido, "facpob07"), tasa_pobreza(unido, "facpob07", unido["urbano"]),
                     tasa_pobreza(unido, "facpob07", ~unido["urbano"]))
    for nombre, valor, ref in (("nacional", nac, REF_POBREZA), ("urbana", urb, REF_URBANA), ("rural", rur, REF_RURAL)):
        v.agregar(f"Informativo: pobreza {nombre} · personas residentes con facpob07", "INFO",
                  f"{valor:.2f} %  (diferencia con la referencia: {valor - ref:+.2f} pp)", f"{ref} %", esencial=False)
    simple = float(100 * unido["pobre"].mean())
    v.agregar("Informativo: pobreza nacional SIN ponderar (no se usa; muestra por qué hay que ponderar)", "INFO",
              f"{simple:.2f} %", "", esencial=False)

    # Decisión de sumaria: ¿cambia algo usar sumaria-2024.dta o sumaria-2024-12g.dta?
    if ruta_12g is None:
        v.agregar("Comparación de sumarias (sumaria-2024 vs sumaria-2024-12g)", "OMITIDA",
                  f"no encontré {SUMARIA_12G} en datos/", "", esencial=False)
    else:
        claves = ["pobreza", "pobrezav", "factor07", "mieperho", "ubigeo", "estrato", "dominio", "gashog2d", "linea", "linpe"]
        g12 = leer(ruta_12g, LLAVES_HOGAR, columnas=None)[LLAVES_HOGAR + claves]
        cmp_ = hogares[LLAVES_HOGAR + claves].merge(g12, on=LLAVES_HOGAR, suffixes=("_a", "_g"), how="outer",
                                                      validate="1:1", indicator=True)
        solo_una = int((cmp_["_merge"] != "both").sum())
        distintas = [c for c in claves if solo_una == 0 and not (
            np.isclose(cmp_[c + "_a"].astype(float), cmp_[c + "_g"].astype(float), equal_nan=True).all()
            if cmp_[c + "_a"].dtype.kind in "fiub" else (cmp_[c + "_a"] == cmp_[c + "_g"]).all())]
        v.comprobar("Las dos sumarias dan lo mismo en hogares y variables de pobreza (justifica la elección de sumaria-2024)",
                    solo_una == 0 and not distintas,
                    f"{len(g12):,} hogares en la 12g; hogares en una sola: {solo_una}; variables distintas: {distintas or 'ninguna'}",
                    "mismos hogares y mismas variables", esencial=False)

    # Escribir validacion.txt siempre; el resto solo si todo lo esencial aprobó
    salidas.mkdir(parents=True, exist_ok=True)
    fallidas = v.esenciales_fallidas()
    lineas = [f"VALIDACIÓN ENAHO {ANIO} · skill limpiando-enaho", "=" * 72,
              f"Módulo 34 (sumaria): {rel(ruta_sum)}", f"Módulo 02 (miembros): {rel(ruta_mie)}", ""]
    for f in v.filas:
        lineas.append(f"[{f['estado']}] {f['nombre']}")
        lineas.append(f"    obtenido: {f['obtenido']}" + (f"   |   esperado: {f['esperado']}" if f["esperado"] else ""))
    n_ok = sum(f["estado"] == "APROBADA" for f in v.filas)
    n_mal = sum(f["estado"] == "FALLIDA" for f in v.filas)
    lineas += ["", "=" * 72, f"RESUMEN: {n_ok} APROBADAS, {n_mal} FALLIDAS",
               "RESULTADO: " + ("TODAS LAS VERIFICACIONES ESENCIALES APROBADAS; se guardaron la base y los indicadores."
                                if not fallidas else
                                "FALLÓ UNA VERIFICACIÓN ESENCIAL; NO se guardó la base. Nada se ajustó para que coincida.")]
    (salidas / "validacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    parquet, csv = salidas / f"personas_{ANIO}.parquet", salidas / "indicadores.csv"
    if fallidas:
        for p in (parquet, csv):
            p.unlink(missing_ok=True)   # no dejar una base anterior que parezca válida
        detalle = "\n".join(f"  - {f['nombre']}: obtenido {f['obtenido']}, esperado {f['esperado']}" for f in fallidas)
        raise Falla(f"Falló {len(fallidas)} verificación(es) esencial(es); no se guardó la base.\n{detalle}\n"
                    f"Revise {rel(salidas / 'validacion.txt')}. No se ajustó ningún resultado.")

    # 7. Guardar la base y los indicadores
    columnas = LLAVES_PERSONA + ["ubigeo", "departamento", "dominio", "estrato", "area", "urbano", "sexo", "edad",
                                 "pobreza", "pobre", "pobre_extremo", "facpob07", "factor07", "mieperho"]
    unido[columnas].to_parquet(parquet, index=False)

    filas = []
    PERSONAS, HOGARES = "personas_facpob07", "hogares_factor07_x_mieperho"

    def indicador(nombre, dimension, categoria, tabla, mascara, peso, metodo, col="pobre"):
        d = tabla if mascara is None else tabla[mascara]
        filas.append({"indicador": nombre, "metodo": metodo, "dimension": dimension, "categoria": categoria,
                      "valor_pct": float(100 * d.loc[d[col], peso].sum() / d[peso].sum()), "n_muestra": len(d),
                      "poblacion_expandida": float(d[peso].sum()), "ponderador": peso, "unidad": "% de personas"})

    for metodo, tabla, peso in ((HOGARES, hog, "w"), (PERSONAS, unido, "facpob07")):
        indicador("pobreza monetaria", "nacional", "Perú", tabla, None, peso, metodo)
        indicador("pobreza extrema", "nacional", "Perú", tabla, None, peso, metodo, col="pobre_extremo")
        for a in ("Urbano", "Rural"):
            indicador("pobreza monetaria", "area", a, tabla, tabla["area"] == a, peso, metodo)
        for d in sorted(DEPARTAMENTOS):
            indicador("pobreza monetaria", "departamento", d, tabla, tabla["departamento"] == d, peso, metodo)
    for sx in ("Hombre", "Mujer"):   # el sexo es un atributo de la persona: solo existe el método por personas
        indicador("pobreza monetaria", "sexo", sx, unido, unido["sexo"] == sx, "facpob07", PERSONAS)
    pd.DataFrame(filas).to_csv(csv, index=False, float_format="%.4f")

    print(f"OK: {len(unido):,} residentes habituales.")
    print(f"  método oficial (hogares, factor07 x mieperho): nacional {nac_h:.2f} %, urbana {urb_h:.2f} %, rural {rur_h:.2f} %")
    print(f"  personas con facpob07: nacional {nac:.2f} %, urbana {urb:.2f} %, rural {rur:.2f} %")
    print(f"  escritos: {rel(parquet)}, {rel(csv)}, {rel(salidas / 'validacion.txt')}")


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):   # acentos correctos también en la consola de Windows
        flujo.reconfigure(encoding="utf-8")
    raiz_por_defecto = Path(__file__).resolve().parents[4]   # .../tarea_4/.claude/skills/limpiando-enaho/scripts/limpiar.py
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", type=Path, default=raiz_por_defecto, help="carpeta del proyecto (tarea_4)")
    ap.add_argument("--datos", type=Path, help="carpeta con los .dta (por defecto <raiz>/datos)")
    ap.add_argument("--salidas", type=Path, help="carpeta de salida (por defecto <raiz>/salidas)")
    a = ap.parse_args()
    raiz = a.raiz.resolve()
    try:
        procesar(raiz, (a.datos or raiz / "datos").resolve(), (a.salidas or raiz / "salidas").resolve())
    except Falla as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
