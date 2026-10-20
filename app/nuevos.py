"""Nuevos descubrimientos: los planetas que el catálogo de los expertos todavía no evalúa."""
from html import escape

import pandas as pd
import streamlit as st

import calculos
import componentes as c
import ficha
import simulador

CANDIDATOS = 6
SOLO_MODELO = ("El modelo lo ve habitable aunque está fuera de la zona habitable del Sol: aprendió que esa zona se "
               "corre según la temperatura de la estrella.")
SOLO_REGLA = ("Cae en la zona habitable del Sol, pero el modelo, que aprendió del criterio de los expertos, le da "
              "menos de 50%.")
COLUMNAS_TABLA = {
    "planeta": st.column_config.TextColumn("Planeta"),
    "probabilidad": st.column_config.ProgressColumn("Habitable según el modelo", min_value=0, max_value=1,
                                                    format="%.2f"),
    "potencialmente_habitable": st.column_config.TextColumn("Mi regla"),
    "esi": st.column_config.NumberColumn("ESI", format="%.3f"),
    "radio_tierras": st.column_config.NumberColumn("Radio (Tierra = 1)", format="%.2f"),
    "insolacion_tierras": st.column_config.NumberColumn("Luz (Tierra = 1)", format="%.2f"),
    "temp_estrella_k": st.column_config.NumberColumn("Estrella (K)", format="%.0f"),
    "anio_descubrimiento": st.column_config.NumberColumn("Descubierto", format="%d"),
}


@st.dialog("Ficha del planeta", width="large")
def _dialogo(df: pd.DataFrame, pred: pd.DataFrame, nombre: str) -> None:
    ficha.mostrar(df, pred, nombre, clave="dialogo_ficha")


def _tarjeta(df: pd.DataFrame, pred: pd.DataFrame, p: pd.Series, clave: str, texto: str = "") -> None:
    with st.container(key=f"tarjeta_{clave}"):
        tipo = calculos.aspecto(p.radio_tierras, p.insolacion_tierras)
        estrella = "estrella sin dato" if pd.isna(p.temp_estrella_k) else f"estrella de {p.temp_estrella_k:,.0f} K"
        anio = "sin dato" if pd.isna(p.anio_descubrimiento) else str(int(p.anio_descubrimiento))
        regla = "Mi regla: sí" if p.potencialmente_habitable != "no" else "Mi regla: no"
        st.html(
            f'<div class="ficha-cabeza">{c.esfera(tipo, 52)}<div><p class="mini-nombre">{escape(p.planeta)}</p>'
            f'<p class="mini-dato">{escape(estrella)} · {anio}</p></div></div>'
            f'<div class="nuevo-prob"><span>{escape(c.porcentaje(p.probabilidad))}</span>habitable según el modelo'
            '</div>'
            + c.barra(p.probabilidad)
            + f'<div class="chips">{c.chip(regla, "habitable" if p.potencialmente_habitable != "no" else "")}'
            f'{c.chip(f"ESI {p.esi:.3f}")}</div>'
            + (f'<p class="nota">{escape(texto)}</p>' if texto else "")
        )
        with st.container(horizontal=True, gap="small"):
            if st.button("Ver ficha", key=f"ver_{clave}", icon=":material/article:", type="tertiary"):
                _dialogo(df, pred, p.planeta)
            st.button("Experimentar", key=f"sim_{clave}", icon=":material/science:", type="tertiary",
                      on_click=simulador.cargar, args=(p.to_dict(),))


def _rejilla(df: pd.DataFrame, pred: pd.DataFrame, filas: pd.DataFrame, prefijo: str,
             textos: pd.Series | None = None) -> None:
    for inicio in range(0, len(filas), 3):
        columnas = st.columns(3, gap="medium")
        for columna, (i, p) in zip(columnas, filas.iloc[inicio:inicio + 3].iterrows()):
            with columna:
                _tarjeta(df, pred, p, f"{prefijo}_{i}", "" if textos is None else textos[i])


def pagina(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    c.encabezado("Después de marzo de 2024", "Nuevos descubrimientos",
                 "El catálogo de habitabilidad de la Universidad de Puerto Rico se actualizó por última vez en marzo "
                 "de 2024. Estos planetas no están en él: los evalúan mi regla y el modelo de machine learning.")
    juntos = (df.merge(pred[["planeta", "probabilidad", "habitable_segun_modelo"]], on="planeta")
              .sort_values(["probabilidad", "esi"], ascending=False).reset_index(drop=True))
    segun_regla = juntos.potencialmente_habitable != "no"
    c.franja([
        (f"{len(juntos):,}", "planetas nuevos", "acento"),
        (f"{int(juntos.habitable_segun_modelo.sum()):,}", "habitables según el modelo", "modelo"),
        (f"{int(segun_regla.sum()):,}", "habitables según mi regla", "habitable"),
        (f"{int((juntos.habitable_segun_modelo & segun_regla).sum()):,}", "en los que coinciden", ""),
    ])

    st.space("medium")
    c.seccion("Los candidatos más fuertes", "según el modelo")
    _rejilla(df, pred, juntos.head(CANDIDATOS), "top")

    distintos = juntos[juntos.habitable_segun_modelo != segun_regla]
    if len(distintos):
        st.space("medium")
        c.seccion("Donde el modelo y mi regla no coinciden", f"{len(distintos)} planetas")
        textos = distintos.habitable_segun_modelo.map({True: SOLO_MODELO, False: SOLO_REGLA})
        _rejilla(df, pred, distintos, "distinto", textos)

    st.space("medium")
    c.seccion("Todos los planetas nuevos", "click en una fila para ver su ficha")
    evento = st.dataframe(juntos[list(COLUMNAS_TABLA)], column_config=COLUMNAS_TABLA, hide_index=True,
                          width="stretch", height=420, on_select="rerun", selection_mode="single-row",
                          key="tabla_nuevos")
    filas = evento.selection.rows
    if not filas:  # al deseleccionar, la misma fila puede volver a abrir su ficha
        st.session_state.pop("_ultimo_tabla_nuevos", None)
    elif st.session_state.get("_ultimo_tabla_nuevos") != filas[0]:
        st.session_state["_ultimo_tabla_nuevos"] = filas[0]
        _dialogo(df, pred, juntos.iloc[filas[0]].planeta)
