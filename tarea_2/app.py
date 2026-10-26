"""Dashboard de la Tarea 2: lee los CSV ya generados por los notebooks, no ejecuta modelos.

Uso, desde tarea_2:

    streamlit run app.py
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATOS = Path(__file__).parent / "datos"   # funciona aunque se lance desde la raiz del repo
EJEMPLOS = DATOS / "ejemplos"             # copias ligeras de imagenes que si se pueden publicar
UMBRAL = 0.90                             # bajo esta confianza una linea de OCR es "dudosa"
TIPOS = ["impreso", "foto", "manuscrito", "audio"]
# un color fijo por tipo, el mismo en todos los graficos; el tipo siempre va tambien escrito
COLORES = {"impreso": "#4C78A8", "foto": "#F58518", "manuscrito": "#54A24B", "audio": "#B279A2"}
NEUTRO = "#8C8C8C"                        # para lo que no es un tipo (veredictos del LLM)


def fuente_de(fila):
    """Grupo de fuente de cada archivo (fuentes.csv tiene el detalle y las licencias)."""
    if fila["modalidad"] == "audio":
        return "OpenSLR 73 (CC BY-SA 4.0)" if fila["id"].startswith("aud_pe") else "Espika FM, entrevista (CC BY-SA 4.0)"
    if fila["archivo"].startswith("Memoria-BCRP"):
        return "BCRP, Memorias 1922-1923"
    if fila["archivo"].startswith("Manuscrito-31"):
        return "PUCP, Carta a Gamarra 1832 (CC0)"
    return "Fotos propias" if fila["tipo"] == "foto" else "Apuntes manuscritos propios"


NOMBRES = {"sintesis reporte marzo 2019": "Reporte de Inflación 2019", "regulacion conceptos": "Regulación económica",
           "hoja calle": "Hoja suelta", "boletas": "Boleta", "caja c digos": "Etiqueta de envío"}


def nombre_corto(ident, largo=28):
    """Nombre legible de un documento a partir de su id; si es largo, se corta por la derecha."""
    if m := re.match(r"imp_Memoria_BCRP_(\d{4})_p0*(\d+)$", ident):
        nombre = f"Memoria BCRP {m[1]}, p. {m[2]}"
    elif m := re.match(r"imp_Manuscrito_31_.*Gamarra_p0*(\d+)$", ident):
        nombre = f"Carta a Gamarra 1832, p. {m[1]}"
    else:
        base = re.sub(r"^(fot_Foto|man_Manuscrito|imp)_", "", ident).replace("_", " ").lower()
        base = re.sub(r"([a-z])(\d)", r"\1 \2", base)          # cuaderno1 -> cuaderno 1
        nombre = NOMBRES.get(base, base.capitalize())
    return nombre if len(nombre) <= largo else nombre[:largo - 1] + "…"


def sin_tildes(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


@st.cache_data
def cargar():
    docs = pd.read_csv(DATOS / "documentos.csv", dtype=str, keep_default_na=False)
    trans = pd.read_csv(DATOS / "transcripciones.csv", dtype=str, keep_default_na=False)
    lineas = pd.read_csv(DATOS / "ocr_lineas.csv", dtype={"texto": str}, keep_default_na=False)
    metricas = pd.read_csv(DATOS / "metricas_linea_base.csv")
    comparativa = pd.read_csv(DATOS / "comparativa_modelos.csv", keep_default_na=False)
    auditoria = pd.read_csv(DATOS / "auditoria_llm.csv", keep_default_na=False)
    llm = pd.read_csv(DATOS / "extraccion_llm.csv", dtype=str, keep_default_na=False).set_index("id")["campos_json"]

    # una sola tabla para buscar y filtrar documentos y audios a la vez
    corpus = pd.concat([
        docs.assign(modalidad="documento", modelo=docs["modelo_ocr"], texto=docs["texto_ocr"],
                    duracion_seg=float("nan")),
        trans.assign(modalidad="audio", tipo="audio", archivo=trans["archivo_audio"], modelo=trans["modelo_asr"],
                     texto=trans["texto_asr"], duracion_seg=trans["duracion_seg"].astype(float)),
    ], ignore_index=True)
    corpus["fuente"] = corpus.apply(fuente_de, axis=1)
    corpus["texto_busqueda"] = corpus["texto"].map(sin_tildes)
    return corpus, lineas, metricas, comparativa, auditoria, llm


def agregado(m):
    """CER o WER agregado de un subconjunto: errores totales / tamano total de las referencias."""
    return (m["valor"] * m["unidades_ref"]).sum() / m["unidades_ref"].sum() if len(m) else None


def estilo(fig, alto=380):
    """Mismo aspecto en todos los graficos: fondo blanco, margenes cortos, titulo a la izquierda."""
    fig.update_layout(template="plotly_white", height=alto, margin=dict(l=10, r=10, t=60, b=10),
                      title_x=0, title_font_size=15, legend_title_text="")
    return fig


def imagen_de(fila):
    """Copia ligera del documento en datos/ejemplos/, si existe (mismo nombre de archivo o el id)."""
    nombres = [fila["archivo"]] + [f"{fila.name}{ext}" for ext in (".jpg", ".jpeg", ".png", ".webp")]
    return next((EJEMPLOS / n for n in nombres if (EJEMPLOS / n).is_file()), None)


def campos_llm(ident):
    if ident in llm.index:
        with st.expander("Campos extraídos por el LLM"):
            st.json(json.loads(llm[ident]))


TITULO = "De documentos escaneados y audio a texto buscable: evaluación sobre un corpus peruano"
st.set_page_config(page_title=TITULO, layout="wide")
corpus, lineas, metricas, comparativa, auditoria, llm = cargar()

# ---------------------------------------------------------------- titulo y respuesta
docs_eval = metricas[metricas["modalidad"] == "documento"]
pct_cifras_mal = 1 - docs_eval["cifras_exactas"].sum() / docs_eval["cifras_total"].sum()
st.title(TITULO)
st.markdown(
    f"##### ¿Se pueden buscar? En parte: el texto se recupera (CER {agregado(docs_eval):.3f}, "
    f"WER {agregado(metricas[metricas['modalidad'] == 'audio']):.3f}), pero el {pct_cifras_mal:.0%} de las "
    f"cifras sale mal y el LLM acierta {auditoria['correcto'].sum()} de {len(auditoria)}: "
    "los montos necesitan revisión humana.")

# ---------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Buscar y filtrar")
    consulta = st.text_input("Buscar en el texto", placeholder="ej.: Lp., encaje, Cusco",
                             help="Sin distinguir mayúsculas ni tildes.")
    tipos = st.multiselect("Tipo", TIPOS, default=TIPOS)
    modelos = st.multiselect("Modelo", sorted(corpus["modelo"].unique()), default=sorted(corpus["modelo"].unique()))
    fuentes = st.multiselect("Fuente", sorted(corpus["fuente"].unique()), default=sorted(corpus["fuente"].unique()))
    dur_max = float(corpus["duracion_seg"].max())
    duracion = st.slider("Duración del audio (s)", 0.0, dur_max, (0.0, dur_max), step=0.5,
                         help="Solo filtra audios.")

filtro = (corpus["tipo"].isin(tipos) & corpus["modelo"].isin(modelos) & corpus["fuente"].isin(fuentes)
          & (corpus["duracion_seg"].isna() | corpus["duracion_seg"].between(*duracion)))
if consulta.strip():
    filtro &= corpus["texto_busqueda"].str.contains(re.escape(sin_tildes(consulta.strip())))
vista = corpus[filtro]
ids = set(vista["id"])
docs_v, aud_v = vista[vista["modalidad"] == "documento"], vista[vista["modalidad"] == "audio"]

# ---------------------------------------------------------------- indicadores
m_doc = metricas[(metricas["modalidad"] == "documento") & metricas["id"].isin(ids)]
m_aud = metricas[(metricas["modalidad"] == "audio") & metricas["id"].isin(ids)]
aud_llm = auditoria[auditoria["id"].isin(ids)]
cer, wer = agregado(m_doc), agregado(m_aud)

st.space("small")
with st.container(border=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Documentos", len(docs_v))
    c2.metric("Minutos de audio", f"{aud_v['duracion_seg'].sum() / 60:.1f}",
              help="Incluye la entrevista de Espika FM, cuyo conductor no es peruano.")
    c3.metric("CER", f"{cer:.3f}" if cer is not None else "—",
              help=f"Error por carácter de PP-OCRv6 (0 = perfecto), en {len(m_doc)} de los 10 documentos "
                   "transcritos a mano que pasan el filtro.")
    c4.metric("WER", f"{wer:.3f}" if wer is not None else "—",
              help=f"Error por palabra de faster-whisper small, en {len(m_aud)} de los 10 clips transcritos a mano.")
    c5.metric("Acuerdo LLM-humano", f"{aud_llm['correcto'].sum()}/{len(aud_llm)}" if len(aud_llm) else "—",
              help="Extracciones correctas según la revisión humana, de las 20 auditadas que pasan el filtro.")
st.caption(f"{len(docs_v)} documentos y {len(aud_v)} audios de {len(corpus)} archivos con los filtros actuales.")
st.space("small")

tab_bus, tab_err, tab_doc, tab_aud, tab_llm, tab_met = st.tabs(
    ["Buscar", "Error de OCR y ASR", "Documentos", "Audio", "Auditoría del LLM", "Metodología"])

# ---------------------------------------------------------------- busqueda
with tab_bus:
    tabla = vista[["id", "tipo", "fuente", "modelo", "duracion_seg", "texto"]].copy()
    if consulta.strip():   # el texto alrededor de la coincidencia
        def extracto(t):
            i = sin_tildes(t).find(sin_tildes(consulta.strip()))
            return ("…" if i > 60 else "") + t[max(0, i - 60):i + 120] + "…"
        tabla["texto"] = tabla["texto"].map(extracto)
    else:
        tabla["texto"] = tabla["texto"].str[:180]
    st.dataframe(tabla, width="stretch", hide_index=True,
                 column_config={"duracion_seg": st.column_config.NumberColumn("duración (s)", format="%.1f")})
    st.download_button("Descargar CSV", vista.drop(columns="texto_busqueda").to_csv(index=False).encode("utf-8"),
                       file_name="corpus_filtrado.csv", mime="text/csv")

# ---------------------------------------------------------------- graficos
with tab_err:
    st.space("small")
    izq, der = st.columns(2, gap="large")
    lin = lineas[lineas["id"].isin(ids)]
    if len(lin):
        por_tipo = (lin.assign(dudosa=lin["confianza"] < UMBRAL)
                    .groupby("tipo").agg(lineas=("linea", "size"), dudosas=("dudosa", "sum")).reset_index())
        por_tipo["pct_dudosas"] = 100 * por_tipo["dudosas"] / por_tipo["lineas"]
        peor = por_tipo.loc[por_tipo["pct_dudosas"].idxmax()]
        fig = px.bar(por_tipo.sort_values("pct_dudosas"), x="tipo", y="pct_dudosas", color="tipo",
                     color_discrete_map=COLORES, text_auto=".0f", hover_data=["lineas", "dudosas"],
                     labels={"pct_dudosas": f"% de líneas con confianza < {UMBRAL}", "tipo": ""},
                     title=f"Los {peor['tipo']}s son los que más dudan: {peor['pct_dudosas']:.0f}% de sus líneas")
        izq.plotly_chart(estilo(fig).update_layout(showlegend=False), width="stretch")
        izq.caption("Confianza del propio modelo, no el error real.")
    else:
        izq.info("Ningún documento pasa el filtro.")

    if len(m_doc):
        # el tipo va escrito en la etiqueta de cada barra: la informacion no depende solo del color
        g = m_doc.assign(documento=m_doc["tipo"] + " · " + m_doc["id"].map(nombre_corto),
                         cifras=m_doc["cifras_exactas"].astype(int).astype(str) + "/" + m_doc["cifras_total"].astype(int).astype(str))
        peor_doc = g.loc[g["valor"].idxmax()]
        fig = px.bar(g.sort_values("valor"), x="valor", y="documento", color="tipo", orientation="h",
                     color_discrete_map=COLORES, category_orders={"tipo": TIPOS}, text_auto=".2f",
                     hover_data={"cifras": True, "valor": ":.3f", "documento": False},
                     labels={"valor": "CER (0 = perfecto)", "documento": "", "cifras": "cifras exactas"},
                     title=f"El error se concentra en pocas páginas: la peor tiene CER {peor_doc['valor']:.2f}")
        der.plotly_chart(estilo(fig, 420), width="stretch")
        der.caption("Documentos transcritos a mano. Las cifras exactas, al pasar el cursor.")
    else:
        der.info("Ninguno de los 10 documentos transcritos a mano pasa el filtro.")

    if len(m_aud):
        st.space("medium")
        g = m_aud.assign(clip=m_aud["id"].str.replace("aud_", "", regex=False))
        fig = px.bar(g.sort_values("valor"), x="clip", y="valor", text_auto=".2f",
                     color_discrete_sequence=[COLORES["audio"]],
                     labels={"valor": "WER (0 = perfecto)", "clip": ""},
                     title=f"El ASR acierta del todo en {(g['valor'] == 0).sum()} de {len(g)} clips; "
                           "en el resto falla en una o dos palabras")
        st.plotly_chart(estilo(fig, 340), width="stretch")

    st.space("medium")
    st.markdown("**Modelos alternativos**")
    st.dataframe(comparativa, width="stretch", hide_index=True)
    st.caption("PaddleOCR-VL, en 4 documentos por su costo en CPU; Parakeet, en los 10 clips.")

# ---------------------------------------------------------------- exploradores
with tab_doc:
    if docs_v.empty:
        st.info("Ningún documento pasa el filtro.")
    else:
        ident = st.selectbox("Documento", docs_v["id"])
        d = docs_v.set_index("id").loc[ident]
        ev = metricas[metricas["id"] == ident]
        datos_ev = (f" · CER {ev['valor'].iloc[0]:.3f} · cifras exactas "
                    f"{int(ev['cifras_exactas'].iloc[0])}/{int(ev['cifras_total'].iloc[0])}") if len(ev) else ""
        st.caption(f"{d['tipo']} · {d['fuente']} · {d['modelo']}{datos_ev}")
        st.space("small")

        imagen = imagen_de(d)
        textos = [("Texto del OCR", d["texto"])]
        if d["texto_referencia"]:
            textos.append(("Transcripción manual", d["texto_referencia"]))
        columnas = st.columns(len(textos) + (imagen is not None), gap="large")
        if imagen is not None:
            try:
                columnas[0].image(str(imagen), caption=imagen.name, width="stretch")
            except Exception:            # imagen danada o formato raro: se sigue solo con el texto
                columnas[0].caption(f"No se pudo mostrar {imagen.name}.")
        for col, (titulo, texto) in zip(columnas[-len(textos):], textos):
            col.markdown(f"**{titulo}**")
            col.text_area(titulo, texto, height=360, label_visibility="collapsed", key=f"{ident}-{titulo}")

        campos_llm(ident)
        lin_doc = lineas[lineas["id"] == ident][["linea", "texto", "confianza"]]
        with st.expander(f"Líneas leídas: {len(lin_doc)}, de ellas {int((lin_doc['confianza'] < UMBRAL).sum())} "
                         f"dudosas (confianza < {UMBRAL})"):
            st.dataframe(lin_doc.assign(dudosa=(lin_doc["confianza"] < UMBRAL).map({True: "sí", False: ""})),
                         width="stretch", hide_index=True)

with tab_aud:
    if aud_v.empty:
        st.info("Ningún audio pasa el filtro.")
    else:
        ident = st.selectbox("Audio", aud_v["id"])
        a = aud_v.set_index("id").loc[ident]
        ev = metricas[metricas["id"] == ident]
        st.caption(f"{a['fuente']} · {a['duracion_seg']:.1f} s · {a['n_hablantes']} hablante(s) · {a['modelo']}"
                   + (f" · WER {ev['valor'].iloc[0]:.3f}" if len(ev) else ""))
        st.space("small")
        segmentos = DATOS / "entrevistas" / f"{ident}.csv"
        if segmentos.exists():
            st.markdown("**Segmentos por hablante**")
            st.dataframe(pd.read_csv(segmentos), width="stretch", hide_index=True)
            st.caption("El nombre del entrevistado está seudonimizado.")
        else:
            st.markdown("**Texto del ASR**")
            st.write(a["texto"])
        if a["texto_referencia"]:
            st.markdown("**Transcripción manual**")
            st.write(a["texto_referencia"])
        campos_llm(ident)
        st.space("small")
        st.caption("Sin reproducción: los audios no se publican y el tramo musical de la entrevista "
                   "tiene derechos de terceros.")

with tab_llm:
    if aud_llm.empty:
        st.info("Ninguna extracción auditada pasa el filtro.")
    else:
        errores = aud_llm.loc[~aud_llm["correcto"], "tipo_error"].value_counts()
        nombre = {"invencion": "invención", "omision": "omisión", "": "correcto"}
        detalle = (f": su error más común es la {nombre.get(errores.index[0], errores.index[0])} "
                   f"({errores.iloc[0]} de {errores.sum()})") if len(errores) else ""
        conteo = aud_llm["tipo_error"].map(lambda t: nombre.get(t, t)).value_counts().reset_index()
        fig = px.bar(conteo, x="tipo_error", y="count", text_auto=True, color_discrete_sequence=[NEUTRO],
                     labels={"tipo_error": "", "count": "extracciones"},
                     title=f"El LLM acierta en {aud_llm['correcto'].sum()} de {len(aud_llm)}{detalle}")
        st.plotly_chart(estilo(fig, 320), width="stretch")
        st.caption("**Omisión:** dejó en `null` algo que el texto permitía llenar. "
                   "**Invención:** afirmó algo que no está en el texto.")
        st.space("small")
        st.dataframe(aud_llm, width="stretch", hide_index=True)

with tab_met:
    st.markdown("""
- **Documentos:** Memorias del BCRP de 1922 y 1923, folleto de 1832, fotos y apuntes propios, leídos con
  **PaddleOCR** (PP-OCRv6). Cada línea trae una confianza entre 0 y 1.
- **Audio:** clips de español peruano de **OpenSLR 73** y una entrevista de radio con 2 hablantes, con
  **faster-whisper `small`** en CPU, detección de voz (VAD) y diarización.
- **Limpieza:** seudonimización de datos personales y duplicados por hash SHA-256.
- **Evaluación:** 10 documentos y 10 clips transcritos a mano (CER y WER), extracción de campos con un LLM
  (Qwen2.5-0.5B) auditada en 20 casos, y comparación con PaddleOCR-VL y Parakeet.

Este tablero solo lee los CSV ya generados: no ejecuta ningún modelo.
""")

# ---------------------------------------------------------------- licencias
st.space("large")
st.divider()
st.caption(
    "**Fuentes y licencias.** Memorias 1922 y 1923: Banco Central de Reserva del Perú, reproducción permitida "
    "citando la fuente · *Carta escrita a Don Agustín Gamarra* (1832): Repositorio PUCP, Instituto Riva-Agüero, "
    "CC0 1.0 · Audio: OpenSLR 73, corpus de español peruano de Google, CC BY-SA 4.0 · Entrevista: Espika FM 90.7, "
    "*Al mundo le falta un tornillo*, 21/11/2020, CC BY-SA 4.0 (el tramo musical no se publica) · Fotos y "
    "apuntes manuscritos: capturas propias de la autora, sin datos personales. Detalle en `datos/fuentes.csv`.")
