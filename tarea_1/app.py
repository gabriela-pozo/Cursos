"""Dashboard de la Tarea 1: clasificador de titulares de El Comercio.

Ejecutar:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).parent
ETIQUETAS = ["politica", "economia", "deportes", "ciencia_tecnologia"]
NOMBRES = {"politica": "Política", "economia": "Economía", "deportes": "Deportes",
           "ciencia_tecnologia": "Ciencia y tecnología"}
REPO_HF = "gabriela-pozo/noticias-pe-distilbert"  # modelo publicado en Hugging Face Hub


# ---------------------------------------------------------------- datos
def leer_noticias(ruta=BASE / "datos" / "noticias.csv"):
    df = pd.read_csv(ruta).fillna({"bajada": ""})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["categoria"] = df["etiqueta"].map(NOMBRES)
    return df


def leer_metricas(ruta=BASE / "modelo" / "metricas.json"):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


# ---------------------------------------------------------- clasificador
def entrenar_ligero(df, ruta_split=BASE / "datos" / "split.csv"):
    """Respaldo sin torch: TF-IDF + regresión logística, entrenado solo con el conjunto train."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    if ruta_split.exists():
        train_urls = set(pd.read_csv(ruta_split).query("split == 'train'")["url"])
        df = df[df["url"].isin(train_urls)]
    modelo = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode"),
                           LogisticRegression(max_iter=1000))
    modelo.fit(df["titular"], df["etiqueta"])

    def predecir(texto):
        return dict(zip(modelo.classes_, modelo.predict_proba([texto])[0]))
    return predecir


def cargar_modelo_fino():
    """Modelo con fine-tuning desde Hugging Face Hub (necesita torch y transformers)."""
    from transformers import pipeline
    clasificador = pipeline("text-classification", model=REPO_HF, top_k=None)

    def predecir(texto):
        return {d["label"]: d["score"] for d in clasificador(texto, truncation=True, max_length=64)[0]}
    return predecir


def obtener_clasificador(df):
    """Devuelve (nombre_del_modelo, función). Prefiere el fine-tuning; si no está, el respaldo ligero."""
    try:
        return f"DistilBERT con fine-tuning ({REPO_HF})", cargar_modelo_fino()
    except Exception:
        return "Respaldo ligero: TF-IDF + regresión logística (no es el modelo de la Parte 2)", entrenar_ligero(df)


# ------------------------------------------------------------- interfaz
def titulo_analitico(df):
    cuenta = df["categoria"].value_counts()
    return f"{cuenta.index[0]} concentra el {cuenta.iloc[0] / len(df):.0%} de las {len(df)} noticias seleccionadas"


@st.cache_data
def noticias():
    return leer_noticias()


@st.cache_data
def metricas_modelo():
    return leer_metricas()


@st.cache_resource(show_spinner="Cargando clasificador...")
def clasificador():
    return obtener_clasificador(noticias())


def main():
    st.set_page_config(page_title="Titulares peruanos", page_icon="📰", layout="wide")
    df, metricas = noticias(), metricas_modelo()

    st.title("📰 Clasificador de titulares peruanos")
    st.caption("Tarea 1 · Titulares de El Comercio (descargados el 17 y 18 de octubre de 2026) "
               "clasificados en política, economía, deportes y ciencia y tecnología.")

    # --- filtros
    st.sidebar.header("Filtros")
    medios = st.sidebar.multiselect("Medio", sorted(df["medio"].unique()), default=sorted(df["medio"].unique()))
    categorias = st.sidebar.multiselect("Categoría", list(NOMBRES.values()), default=list(NOMBRES.values()))
    filtrado = df[df["medio"].isin(medios) & df["categoria"].isin(categorias)]
    if filtrado.empty:
        st.warning("No hay noticias con esos filtros. Amplía la selección en la barra lateral.")
        st.stop()

    # --- métricas
    f1 = metricas.get("f1_macro_test")
    acuerdo = metricas.get("acuerdo_llm_humano_de_20")
    c1, c2, c3 = st.columns(3)
    c1.metric("Noticias (según filtros)", f"{len(filtrado)} de {len(df)}")
    c2.metric("F1 macro en test", f"{f1:.2f}" if f1 is not None else "—")
    c3.metric("Acuerdo LLM-humano", f"{acuerdo}/20 ({acuerdo / 20:.0%})" if acuerdo is not None else "—")

    # --- gráficos
    izq, der = st.columns(2)
    por_categoria = filtrado["categoria"].value_counts().rename_axis("categoria").reset_index(name="noticias")
    fig1 = px.bar(por_categoria, x="categoria", y="noticias", text="noticias", title=titulo_analitico(filtrado))
    fig1.update_layout(xaxis_title=None, yaxis_title="Noticias")
    izq.plotly_chart(fig1, width="stretch")

    por_dia = filtrado.groupby([filtrado["fecha"].dt.date.rename("fecha"), "categoria"]).size().reset_index(name="noticias")
    fig2 = px.bar(por_dia, x="fecha", y="noticias", color="categoria", title="Publicaciones por día y categoría")
    fig2.update_layout(xaxis_title=None, yaxis_title="Noticias", legend_title=None)
    der.plotly_chart(fig2, width="stretch")

    # --- tabla
    st.subheader("Noticias")
    st.dataframe(filtrado[["fecha", "medio", "categoria", "titular", "bajada", "url"]], width="stretch", hide_index=True,
                 column_config={"url": st.column_config.LinkColumn("enlace", display_text="abrir")})
    st.download_button("⬇️ Descargar selección en CSV", filtrado.to_csv(index=False).encode("utf-8"),
                       "noticias_filtradas.csv", "text/csv")

    # --- clasificador en vivo
    st.subheader("Clasifica un titular")
    texto = st.text_area("Escribe o pega un titular", placeholder="Ej.: El BCR mantiene su tasa de referencia en 4.5%")
    if st.button("Clasificar", type="primary") and texto.strip():
        nombre_modelo, predecir = clasificador()
        probs = predecir(texto.strip())
        mejor = max(probs, key=probs.get)
        st.success(f"Categoría: **{NOMBRES.get(mejor, mejor)}** · probabilidad {probs[mejor]:.0%}")
        tabla = pd.DataFrame({"categoria": [NOMBRES.get(k, k) for k in probs], "probabilidad": list(probs.values())})
        fig3 = px.bar(tabla.sort_values("probabilidad"), x="probabilidad", y="categoria", orientation="h",
                      range_x=[0, 1], title="Probabilidad por categoría")
        fig3.update_layout(yaxis_title=None)
        st.plotly_chart(fig3, width="stretch")
        st.caption(f"Modelo usado: {nombre_modelo}")


if __name__ == "__main__":
    main()
