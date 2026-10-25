"""Dashboard de la Tarea 2: lee los CSV ya generados por los notebooks, no ejecuta modelos.

Uso, desde tarea_2:

    streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATOS = Path(__file__).parent / "datos"   # funciona aunque se lance desde la raiz del repo
UMBRAL = 0.90                             # bajo esta confianza una linea de OCR es "dudosa"
COLORES = {"impreso": "#4C78A8", "foto": "#F58518", "manuscrito": "#54A24B"}


@st.cache_data
def cargar():
    docs = pd.read_csv(DATOS / "documentos.csv", dtype=str, keep_default_na=False)
    trans = pd.read_csv(DATOS / "transcripciones.csv", keep_default_na=False)
    lineas = pd.read_csv(DATOS / "ocr_lineas.csv", dtype={"texto": str}, keep_default_na=False)
    return docs, trans, lineas


st.set_page_config(page_title="Archivos económicos del Perú: ¿se pueden buscar?", layout="wide")
docs, trans, lineas = cargar()

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

Este tablero solo lee los CSV ya generados: no ejecuta ningún modelo.
""")

clips = trans[trans["id"].str.startswith("aud_pe")]
c1, c2 = st.columns(2)
c1.metric("Documentos", len(docs))
c2.metric("Minutos de audio", f"{trans['duracion_seg'].sum() / 60:.1f}",
          help=f"{clips['duracion_seg'].sum() / 60:.1f} min son de español peruano (OpenSLR 73); "
               "el resto es la entrevista, cuyo conductor no es peruano.")

st.subheader("Dónde duda el OCR")
por_tipo = (lineas.assign(dudosa=lineas["confianza"] < UMBRAL)
            .groupby("tipo").agg(lineas=("linea", "size"), dudosas=("dudosa", "sum")).reset_index())
por_tipo["pct_dudosas"] = 100 * por_tipo["dudosas"] / por_tipo["lineas"]
peor = por_tipo.loc[por_tipo["pct_dudosas"].idxmax()]
fig = px.bar(por_tipo.sort_values("pct_dudosas"), x="tipo", y="pct_dudosas", color="tipo",
             color_discrete_map=COLORES, text_auto=".0f", hover_data=["lineas", "dudosas"],
             labels={"pct_dudosas": f"% de líneas con confianza < {UMBRAL}", "tipo": ""},
             title=f"Los {peor['tipo']}s son los que más dudan: {peor['pct_dudosas']:.0f}% de sus líneas")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, width="stretch")
st.caption("La confianza es lo que el modelo cree de sí mismo, no el error real: "
           "el error (CER) se mide contra transcripciones hechas a mano.")

st.subheader("Documentos")
st.dataframe(docs, width="stretch", hide_index=True)
st.download_button("Descargar documentos.csv", docs.to_csv(index=False).encode("utf-8"),
                   file_name="documentos.csv", mime="text/csv")
