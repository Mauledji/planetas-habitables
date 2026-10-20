"""El sandbox: traer un planeta (real o inventado), cambiarle valores y ver en 3D qué dice el modelo."""
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

import calculos
import componentes as c
import graficas
import sandbox3d

TIERRA = {"planeta": "Tierra", "estrella": "El Sol", "radio_tierras": 1.0, "insolacion_tierras": 1.0,
          "temp_estrella_k": 5778}
PRESETS = ["Tierra", "TRAPPIST-1 e", "Proxima Cen b", "Teegarden's Star b", "Kepler-452 b", "Gliese 48 b"]
TEMP_MIN, TEMP_MAX = 2500, 7000
LARGO_NOMBRE = 120


def _texto(valor) -> str | None:
    return None if valor is None or pd.isna(valor) else str(valor)[:LARGO_NOMBRE]


def _guardar(nombre: str, estrella: str | None, radio: float, luz: float, temp: float) -> None:
    st.session_state["sim_nombre"] = nombre
    st.session_state["sim_estrella"] = estrella
    st.session_state["sim_radio"] = float(np.clip(radio, calculos.RADIO_MIN, calculos.RADIO_MAX))
    st.session_state["sim_luz"] = float(np.clip(luz, calculos.LUZ_MIN, calculos.LUZ_MAX))
    st.session_state["sim_temp"] = int(np.clip(round(temp / 10) * 10, TEMP_MIN, TEMP_MAX))


def _poner(planeta: dict) -> None:
    """Pone un planeta en el simulador. Sube la versión para que la vista 3D lo tome."""
    temp = planeta.get("temp_estrella_k")
    _guardar(str(planeta["planeta"]), _texto(planeta.get("estrella")), float(planeta["radio_tierras"]),
             max(float(planeta["insolacion_tierras"]), 1e-6), 5778.0 if temp is None or pd.isna(temp) else float(temp))
    st.session_state["sim_version"] = st.session_state.get("sim_version", 0) + 1


def _desde_3d() -> None:
    """Callback: lo que se movió en la vista 3D (llega al soltar un control). Se valida porque viene del navegador."""
    valores = (st.session_state.get("sim3d") or {}).get("planeta")
    if not isinstance(valores, dict):
        return
    try:
        _guardar(_texto(valores.get("nombre")) or "Tu planeta", _texto(valores.get("estrella")),
                 float(valores["radio"]), float(valores["luz"]), float(valores["temp"]))
    except (KeyError, TypeError, ValueError):
        return


def cargar(planeta: dict) -> None:
    """Callback: pone los datos de un planeta en el simulador y pide abrir la página."""
    _poner(planeta)
    st.session_state["ir_a"] = "experimentar"


def iniciar() -> None:
    if "sim_nombre" not in st.session_state:
        _poner(TIERRA)


def _fila(df: pd.DataFrame, nombre: str) -> dict | None:
    if nombre == "Tierra":
        return TIERRA
    filas = df[df.planeta == nombre]
    return None if filas.empty else filas.iloc[0].to_dict()


def _presets(df: pd.DataFrame) -> None:
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        st.html('<span class="ceja" style="margin:0">Probar con</span>', width="content")
        for nombre in PRESETS:
            fila = _fila(df, nombre)
            if fila is not None:
                st.button(nombre, key=f"preset_{nombre}", on_click=_poner, args=(fila,), type="secondary")


def _mapa(df: pd.DataFrame, modelo, radio: float, luz: float, temp: float) -> None:
    if modelo is None:
        return
    luz_grilla, radio_grilla, prob = calculos.grilla(modelo, temp)
    parecidos = df[(df.temp_estrella_k - temp).abs() <= 400]
    c.seccion("Dónde ve vida el modelo", f"estrella de {temp:,} K · {len(parecidos):,} planetas reales parecidos")
    with st.container(key="panel_mapa_modelo"):
        st.plotly_chart(graficas.mapa_modelo(luz_grilla, radio_grilla, prob, parecidos, (luz, radio)),
                        theme=None, config=graficas.CONFIG, width="stretch")
        st.html('<p class="nota">Lo violeta es donde el modelo considera habitable un planeta alrededor de esta '
                'estrella, y la línea marca dónde pasa de "no" a "sí". Ojo: casi no hay planetas del tamaño de la '
                'Tierra alrededor de estrellas como el Sol (son los más difíciles de detectar), así que ahí el modelo '
                'duda más y la misma Tierra no le sale al 100%.</p>')


def _parecidos(df: pd.DataFrame, radio: float, luz: float, temp: float) -> None:
    distancia = ((np.log10(df.insolacion_tierras.clip(lower=1e-4)) - np.log10(luz)) ** 2
                 + (np.log10(df.radio_tierras) - np.log10(radio)) ** 2
                 + ((df.temp_estrella_k.fillna(5778) - temp) / 1000) ** 2)
    cercanos = df.assign(distancia=distancia).nsmallest(5, "distancia")
    c.seccion("Los planetas reales más parecidos", "click para traerlo al simulador")
    for i, (columna, (_, p)) in enumerate(zip(st.columns(5), cercanos.iterrows())):
        with columna, st.container(key=f"tarjeta_parecido_{i}"):
            tipo = calculos.aspecto(p.radio_tierras, p.insolacion_tierras)
            estrella = "sin dato" if pd.isna(p.temp_estrella_k) else f"{p.temp_estrella_k:,.0f} K"
            st.html(f'{c.esfera(tipo, 44)}<p class="mini-nombre">{escape(p.planeta)}</p>'
                    f'<p class="mini-dato">ESI {p.esi:.3f} · {estrella}</p>')
            st.button("Traer", key=f"parecido_{p.planeta}", icon=":material/arrow_upward:", type="tertiary",
                      on_click=_poner, args=(p.to_dict(),))


def pagina(df: pd.DataFrame, modelo) -> None:
    c.encabezado("Sandbox del modelo", "Experimentar",
                 "Arma un planeta o trae uno real y mueve sus valores: la estrella, su zona habitable y el planeta "
                 "cambian en vivo, y el modelo da su veredicto al instante. Aprendió del criterio de los expertos de "
                 "la UPR con los planetas que ellos sí evaluaron.")
    _presets(df)
    sandbox3d.mostrar({"nombre": st.session_state["sim_nombre"], "estrella": st.session_state["sim_estrella"],
                       "radio": st.session_state["sim_radio"], "luz": st.session_state["sim_luz"],
                       "temp": st.session_state["sim_temp"]},
                      st.session_state["sim_version"], modelo, _desde_3d)
    st.html('<p class="nota">La franja verde es la zona habitable de esa estrella según Kopparapu et al. (2014): con '
            'una enana roja se corre hacia donde llega menos luz. La línea punteada es mi regla, que siempre usa la '
            'zona del Sol, y por eso a veces no coincide con el modelo. Las distancias y los tamaños no están a escala: '
            'el planeta se dibuja a la distancia que le daría esa luz.</p>')
    radio, luz, temp = (st.session_state[clave] for clave in ("sim_radio", "sim_luz", "sim_temp"))
    _mapa(df, modelo, radio, luz, temp)
    _parecidos(df, radio, luz, temp)
