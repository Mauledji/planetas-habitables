"""Explorar: el mapa de todos los planetas, la ficha del elegido y el ranking por parecido a la Tierra."""
import pandas as pd
import streamlit as st

import componentes as c
import ficha
import graficas

TODOS, HABITABLES = "Todos", "Potencialmente habitables"
RADIO_FILTRO, LUZ_FILTRO, DISTANCIA_FILTRO = (0.0, 6.0), (0.0, 5.0), 5000
COLUMNAS_TABLA = {
    "planeta": st.column_config.TextColumn("Planeta"),
    "esi": st.column_config.ProgressColumn("Parecido a la Tierra (ESI)", min_value=0, max_value=1, format="%.3f"),
    "potencialmente_habitable": st.column_config.TextColumn("Mi regla"),
    "radio_tierras": st.column_config.NumberColumn("Radio (Tierra = 1)", format="%.2f"),
    "insolacion_tierras": st.column_config.NumberColumn("Luz (Tierra = 1)", format="%.2f"),
    "distancia_anios_luz": st.column_config.NumberColumn("Años luz", format="%.0f"),
    "estrella": st.column_config.TextColumn("Estrella"),
    "anio_descubrimiento": st.column_config.NumberColumn("Descubierto", format="%d"),
}


# Los callbacks corren antes de dibujar la página, solo cuando hay un click nuevo:
# así el mapa ya marca el planeta recién elegido y un filtro no cambia la ficha por su cuenta.
def _al_click_en_mapa() -> None:
    puntos = (st.session_state.get("mapa") or {}).get("selection", {}).get("points", [])
    dato = puntos[0].get("customdata") if puntos else None
    nombre = dato[0] if isinstance(dato, list) else dato
    if nombre:
        st.session_state["planeta"] = nombre


def _al_elegir_fila() -> None:
    filas = (st.session_state.get("tabla_explorar") or {}).get("selection", {}).get("rows", [])
    planetas = st.session_state.get("_planetas_tabla", [])
    if filas and filas[0] < len(planetas):
        st.session_state["planeta"] = planetas[filas[0]]


def _al_buscar() -> None:
    if st.session_state.get("buscar"):
        st.session_state["planeta"] = st.session_state["buscar"]
        st.session_state["buscar"] = None  # el buscador queda listo para otra búsqueda


def _filtros(df: pd.DataFrame) -> pd.DataFrame:
    with st.container(horizontal=True, gap="small", vertical_alignment="bottom"):
        st.selectbox("Buscar un planeta", sorted(df.planeta), index=None, key="buscar", on_change=_al_buscar,
                     placeholder="Buscar un planeta, por ejemplo TRAPPIST-1 e", label_visibility="collapsed",
                     width=340)
        mostrar = st.segmented_control("Mostrar", [TODOS, HABITABLES], default=TODOS, key="mostrar",
                                       label_visibility="collapsed", persist_state="session")
        with st.popover("Filtros", icon=":material/tune:"):
            radio = st.slider("Radio (Tierra = 1)", *RADIO_FILTRO, RADIO_FILTRO, 0.1, key="filtro_radio",
                              persist_state="session")
            luz = st.slider("Luz que recibe (Tierra = 1)", *LUZ_FILTRO, LUZ_FILTRO, 0.05, key="filtro_luz",
                            persist_state="session")
            distancia = st.slider("Distancia máxima (años luz)", 10, DISTANCIA_FILTRO, DISTANCIA_FILTRO, 10,
                                  key="filtro_distancia", persist_state="session")
    filtrado = df[df.radio_tierras.between(*radio) & df.insolacion_tierras.between(*luz)]
    filtrado = filtrado[filtrado.distancia_anios_luz.isna() | (filtrado.distancia_anios_luz <= distancia)]
    if mostrar == HABITABLES:
        filtrado = filtrado[filtrado.potencialmente_habitable != "no"]
    return filtrado.sort_values("esi", ascending=False).reset_index(drop=True)


def _portada(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    c.encabezado("NASA Exoplanet Archive · Habitable Worlds Catalog", "¿Hay otra Tierra?",
                 "Todos los planetas confirmados por la NASA, qué tanto se parecen a la Tierra y qué diría un modelo "
                 "entrenado con el criterio de los expertos del Habitable Worlds Catalog (PHL @ UPR Arecibo).",
                 principal=True)
    c.franja([
        (f"{len(df):,}", "planetas evaluados", "acento"),
        (f"{(df.potencialmente_habitable != 'no').sum():,}", "potencialmente habitables (mi regla)", "habitable"),
        (f"{len(pred):,}", "nuevos, sin evaluar por expertos", ""),
        (f"{int(pred.habitable_segun_modelo.sum()):,}", "habitables según el modelo", "modelo"),
    ])


def pagina(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    _portada(df, pred)
    st.space("medium")
    filtrado = _filtros(df)
    st.session_state.setdefault("planeta", df.sort_values("esi").planeta.iloc[-1])

    mapa, detalle = st.columns([3, 2], gap="large")
    with mapa, st.container(key="panel_mapa"):
        st.plotly_chart(graficas.mapa_planetas(filtrado, st.session_state["planeta"]), key="mapa", theme=None,
                        on_select=_al_click_en_mapa, selection_mode="points", config=graficas.CONFIG,
                        width="stretch")
        st.html('<div class="leyenda"><span>Cada punto es un planeta, con el color de su estrella:</span>'
                '<span class="leyenda__escala"></span><span class="mono">2,500 K → 7,500 K</span></div>')
    with detalle:
        ficha.mostrar(df, pred, st.session_state["planeta"])

    st.space("medium")
    c.seccion("Ranking por parecido a la Tierra", f"{len(filtrado):,} planetas con estos filtros")
    st.session_state["_planetas_tabla"] = list(filtrado.planeta)  # para saber qué planeta es cada fila al hacer click
    st.dataframe(filtrado[list(COLUMNAS_TABLA)], column_config=COLUMNAS_TABLA, hide_index=True, width="stretch",
                 height=420, on_select=_al_elegir_fila, selection_mode="single-row", key="tabla_explorar")
