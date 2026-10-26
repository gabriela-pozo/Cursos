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
UMBRAL = 0.90                             # bajo esta confianza una linea de OCR es "dudosa"
COLORES = {"impreso": "#4C78A8", "foto": "#F58518", "manuscrito": "#54A24B", "audio": "#B279A2"}
TIPOS = ["impreso", "foto", "manuscrito", "audio"]


def fuente_de(fila):
    """Grupo de fuente de cada archivo (fuentes.csv tiene el detalle y las licencias)."""
    if fila["modalidad"] == "audio":
        return "OpenSLR 73 (CC BY-SA 4.0)" if fila["id"].startswith("aud_pe") else "Espika FM, entrevista (CC BY-SA 4.0)"
    if fila["archivo"].startswith("Memoria-BCRP"):
        return "BCRP, Memorias 1922-1923"
    if fila["archivo"].startswith("Manuscrito-31"):
        return "PUCP, Carta a Gamarra 1832 (CC0)"
    return "Fotos propias" if fila["tipo"] == "foto" else "Apuntes manuscritos propios"


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


st.set_page_config(page_title="Archivos económicos del Perú: ¿se pueden buscar?", layout="wide")
corpus, lineas, metricas, comparativa, auditoria, llm = cargar()

st.title("Archivos económicos del Perú: ¿se pueden buscar?")
st.markdown("""
**Pregunta.** Los archivos históricos económicos del Perú están digitalizados, pero ¿se puede buscar
en ellos? Se mide el error de OCR y ASR, y cuánta revisión humana hace falta antes de confiar en las cifras.

**Método.**
- **Documentos:** páginas impresas (Memorias del BCRP de 1922 y 1923, folleto de 1832), fotos propias
  y manuscritos propios, leídos con **PaddleOCR** (PP-OCRv6, con corrección de orientación).
  Cada línea leída trae una confianza entre 0 y 1.
- **Audio:** clips de español peruano de **OpenSLR 73** y una entrevista de radio con 2 hablantes,
  transcritos con **faster-whisper `small`** en CPU, con detección de voz (VAD) y diarización.
- **Limpieza:** seudonimización de datos personales y eliminación de duplicados por hash SHA-256.
- **Evaluación:** muestra fija de 10 documentos y 10 clips transcritos a mano (CER y WER), extracción
  de campos con un LLM (Qwen2.5-0.5B) auditada a mano en 20 casos, y comparación con PaddleOCR-VL y Parakeet.

Este tablero solo lee los CSV ya generados: no ejecuta ningún modelo.
""")

# ---------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Búsqueda y filtros")
    consulta = st.text_input("Buscar en el texto", placeholder="ej.: Lp., encaje, Cusco",
                             help="Busca en el texto del OCR y del ASR, sin distinguir mayúsculas ni tildes.")
    tipos = st.multiselect("Tipo", TIPOS, default=TIPOS)
    modelos = st.multiselect("Modelo", sorted(corpus["modelo"].unique()), default=sorted(corpus["modelo"].unique()))
    fuentes = st.multiselect("Fuente", sorted(corpus["fuente"].unique()), default=sorted(corpus["fuente"].unique()))
    dur_max = float(corpus["duracion_seg"].max())
    duracion = st.slider("Duración del audio (s)", 0.0, dur_max, (0.0, dur_max), step=0.5,
                         help="Solo filtra audios; los documentos no tienen duración.")

filtro = (corpus["tipo"].isin(tipos) & corpus["modelo"].isin(modelos) & corpus["fuente"].isin(fuentes)
          & (corpus["duracion_seg"].isna() | corpus["duracion_seg"].between(*duracion)))
if consulta.strip():
    filtro &= corpus["texto_busqueda"].str.contains(re.escape(sin_tildes(consulta.strip())))
vista = corpus[filtro]
ids = set(vista["id"])
docs_v, aud_v = vista[vista["modalidad"] == "documento"], vista[vista["modalidad"] == "audio"]
st.caption(f"Mostrando {len(docs_v)} documentos y {len(aud_v)} audios de {len(corpus)} archivos.")

# ---------------------------------------------------------------- indicadores
m_doc = metricas[(metricas["modalidad"] == "documento") & metricas["id"].isin(ids)]
m_aud = metricas[(metricas["modalidad"] == "audio") & metricas["id"].isin(ids)]
aud_llm = auditoria[auditoria["id"].isin(ids)]
cer, wer = agregado(m_doc), agregado(m_aud)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Documentos", len(docs_v))
c2.metric("Minutos de audio", f"{aud_v['duracion_seg'].sum() / 60:.1f}",
          help="Incluye la entrevista de Espika FM, cuyo conductor no es peruano.")
c3.metric("CER (línea base)", f"{cer:.3f}" if cer is not None else "—",
          help=f"PP-OCRv6 en {len(m_doc)} de los 10 documentos con transcripción manual que pasan el filtro. "
               "Agregado: errores totales / caracteres de la referencia. 0 = perfecto.")
c4.metric("WER (línea base)", f"{wer:.3f}" if wer is not None else "—",
          help=f"faster-whisper small en {len(m_aud)} de los 10 clips con transcripción manual que pasan el filtro.")
c5.metric("Concordancia LLM-humano", f"{aud_llm['correcto'].sum()}/{len(aud_llm)}" if len(aud_llm) else "—",
          help="Extracciones del LLM que la revisión humana dio por correctas, de las 20 auditadas que pasan el filtro.")

tab_res, tab_err, tab_doc, tab_aud, tab_llm = st.tabs(
    ["Resultados", "Error de OCR y ASR", "Explorador de documentos", "Explorador de audio", "Auditoría del LLM"])

# ---------------------------------------------------------------- resultados de la busqueda
with tab_res:
    tabla = vista[["id", "modalidad", "tipo", "fuente", "modelo", "duracion_seg", "texto"]].copy()
    if consulta.strip():   # mostrar el texto alrededor de la coincidencia
        def extracto(t):
            i = sin_tildes(t).find(sin_tildes(consulta.strip()))
            return ("…" if i > 60 else "") + t[max(0, i - 60):i + 120] + "…"
        tabla["texto"] = tabla["texto"].map(extracto)
    else:
        tabla["texto"] = tabla["texto"].str[:180]
    st.dataframe(tabla, width="stretch", hide_index=True)
    st.download_button("Descargar la tabla filtrada (CSV)",
                       vista.drop(columns="texto_busqueda").to_csv(index=False).encode("utf-8"),
                       file_name="corpus_filtrado.csv", mime="text/csv")

# ---------------------------------------------------------------- graficos
with tab_err:
    izq, der = st.columns(2)
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
        fig.update_layout(showlegend=False)
        izq.plotly_chart(fig, width="stretch")
        izq.caption("La confianza es lo que el modelo cree de sí mismo, no el error real.")
    else:
        izq.info("Ningún documento pasa el filtro.")

    if len(m_doc):
        g = m_doc.assign(documento=m_doc["id"].str.replace(r"^(imp|fot|man)_", "", regex=True).str[-30:],
                         cifras=m_doc["cifras_exactas"].astype(int).astype(str) + "/" + m_doc["cifras_total"].astype(int).astype(str))
        peor_doc = g.loc[g["valor"].idxmax()]
        fig = px.bar(g.sort_values("valor"), x="valor", y="documento", color="tipo", orientation="h",
                     color_discrete_map=COLORES, hover_data={"cifras": True, "valor": ":.3f"},
                     labels={"valor": "CER (0 = perfecto)", "documento": "", "cifras": "cifras exactas"},
                     title=f"El error se concentra en pocas páginas: la peor ({peor_doc['documento'][:22]}) "
                           f"tiene CER {peor_doc['valor']:.2f}")
        fig.update_layout(height=420)
        der.plotly_chart(fig, width="stretch")
        der.caption("Solo los documentos con transcripción manual. Pasa el cursor para ver las cifras "
                    "(montos, fechas y %) leídas exactas.")
    else:
        der.info("Ninguno de los 10 documentos con transcripción manual pasa el filtro.")

    if len(m_aud):
        g = m_aud.assign(clip=m_aud["id"].str.replace("aud_", "", regex=False))
        fig = px.bar(g.sort_values("valor"), x="clip", y="valor", color_discrete_sequence=[COLORES["audio"]],
                     labels={"valor": "WER (0 = perfecto)", "clip": ""},
                     title=f"El ASR acierta del todo en {(g['valor'] == 0).sum()} de {len(g)} clips; "
                           "los errores son de una o dos palabras")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Comparativa con modelos alternativos")
    st.dataframe(comparativa, width="stretch", hide_index=True)
    st.caption("PaddleOCR-VL se evaluó en 4 documentos (impreso, manuscrito, boleta y página a dos columnas) "
               "por su costo en CPU; Parakeet en los 10 clips. Detalle y decisión en 02_evaluacion.ipynb.")


def campos_llm(ident):
    if ident in llm.index:
        st.markdown("**Campos extraídos por el LLM** (sin revisar, salvo los 20 auditados)")
        st.json(json.loads(llm[ident]))


# ---------------------------------------------------------------- exploradores
with tab_doc:
    if docs_v.empty:
        st.info("Ningún documento pasa el filtro.")
    else:
        ident = st.selectbox("Documento", docs_v["id"])
        d = docs_v.set_index("id").loc[ident]
        st.markdown(f"**Tipo:** {d['tipo']} · **Fuente:** {d['fuente']} · **Modelo:** {d['modelo']}")
        ev = metricas[metricas["id"] == ident]
        if len(ev):
            st.markdown(f"**CER:** {ev['valor'].iloc[0]:.3f} · **cifras exactas:** "
                        f"{int(ev['cifras_exactas'].iloc[0])}/{int(ev['cifras_total'].iloc[0])}")
        a, b = st.columns(2)
        a.markdown("**Texto del OCR**")
        a.text_area("ocr", d["texto"], height=320, label_visibility="collapsed")
        if d["texto_referencia"]:
            b.markdown("**Transcripción manual (referencia)**")
            b.text_area("ref", d["texto_referencia"], height=320, label_visibility="collapsed")
        else:
            with b:
                campos_llm(ident)
        if d["texto_referencia"]:
            campos_llm(ident)
        lin_doc = lineas[lineas["id"] == ident][["linea", "texto", "confianza"]]
        st.markdown(f"**Líneas leídas** ({len(lin_doc)}; {int((lin_doc['confianza'] < UMBRAL).sum())} dudosas)")
        st.dataframe(lin_doc.style.map(lambda c: "color: #c0392b" if c < UMBRAL else "", subset=["confianza"]),
                     width="stretch", hide_index=True)

with tab_aud:
    if aud_v.empty:
        st.info("Ningún audio pasa el filtro.")
    else:
        ident = st.selectbox("Audio", aud_v["id"])
        a = aud_v.set_index("id").loc[ident]
        st.markdown(f"**Fuente:** {a['fuente']} · **Duración:** {a['duracion_seg']:.1f} s · "
                    f"**Hablantes:** {a['n_hablantes']} · **Modelo:** {a['modelo']}")
        ev = metricas[metricas["id"] == ident]
        if len(ev):
            st.markdown(f"**WER:** {ev['valor'].iloc[0]:.3f}")
        segmentos = DATOS / "entrevistas" / f"{ident}.csv"
        if segmentos.exists():
            seg = pd.read_csv(segmentos)
            st.markdown("**Segmentos por hablante** (diarización; el nombre del entrevistado está seudonimizado)")
            st.dataframe(seg, width="stretch", hide_index=True)
        else:
            st.markdown("**Texto del ASR**")
            st.write(a["texto"])
        if a["texto_referencia"]:
            st.markdown("**Transcripción manual (referencia)**")
            st.write(a["texto_referencia"])
        campos_llm(ident)
        st.info("El audio no se reproduce aquí: los archivos de audio no se publican en el repositorio "
                "(datos/raw no se versiona) y el tramo musical de la entrevista tiene derechos de terceros "
                "sin permiso de publicación.")

with tab_llm:
    st.markdown("20 extracciones elegidas al azar (semilla 20261025) y revisadas a mano. "
                "**Omisión:** dejó en `null` algo que el texto permitía llenar. "
                "**Invención:** afirmó algo que no está en el texto.")
    st.dataframe(aud_llm, width="stretch", hide_index=True)
    if len(aud_llm):
        errores = aud_llm.loc[~aud_llm["correcto"], "tipo_error"].value_counts()
        detalle = f": su error más común es la {errores.index[0].replace('invencion', 'invención').replace('omision', 'omisión')} ({errores.iloc[0]} de {errores.sum()})" if len(errores) else ""
        conteo = aud_llm["tipo_error"].replace("", "correcto").value_counts().reset_index()
        fig = px.bar(conteo, x="tipo_error", y="count", text_auto=True,
                     labels={"tipo_error": "", "count": "extracciones"},
                     title=f"El LLM acierta en {aud_llm['correcto'].sum()} de {len(aud_llm)}{detalle}")
        st.plotly_chart(fig, width="stretch")
