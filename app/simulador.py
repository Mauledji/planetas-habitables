"""El sandbox: traer un planeta (real o inventado), cambiarle valores y ver qué dice el modelo."""
import numpy as np
import pandas as pd
import streamlit as st

import calculos
import graficas

VISTA = "🧪 Experimentar"
OPCIONES_LUZ = [round(float(v), 3) for v in np.logspace(np.log10(calculos.LUZ_MIN), np.log10(calculos.LUZ_MAX), 121)]
TIERRA = {"planeta": "Tierra", "radio_tierras": 1.0, "insolacion_tierras": 1.0, "temp_estrella_k": 5778}
PRESETS = ["Tierra", "TRAPPIST-1 e", "Teegarden's Star b", "Kepler-452 b"]
TEXTO_REGLA = {"conservador": "habitable (criterio conservador)", "optimista": "habitable (criterio optimista)",
               "no": "no habitable"}


def _poner(planeta: dict) -> None:
    luz = max(float(planeta["insolacion_tierras"]), 1e-6)
    temp = planeta.get("temp_estrella_k")
    temp = 5778 if temp is None or pd.isna(temp) else float(temp)
    st.session_state["sim_nombre"] = planeta["planeta"]
    st.session_state["sim_radio"] = float(np.clip(round(planeta["radio_tierras"], 2), calculos.RADIO_MIN, calculos.RADIO_MAX))
    st.session_state["sim_luz"] = min(OPCIONES_LUZ, key=lambda o: abs(np.log10(o) - np.log10(luz)))
    st.session_state["sim_temp"] = int(np.clip(round(temp / 10) * 10, 2500, 7000))


def cargar(planeta: dict) -> None:
    """Callback: pone los datos de un planeta en los controles y abre el simulador."""
    _poner(planeta)
    st.session_state["vista"] = VISTA


def iniciar() -> None:
    if "sim_nombre" not in st.session_state:
        _poner(TIERRA)


def _inventado() -> None:
    nombre = st.session_state["sim_nombre"]
    if not nombre.startswith("Tu planeta"):
        st.session_state["sim_nombre"] = "Tu planeta" if nombre == "Tierra" else f"Tu planeta (a partir de {nombre})"


def _fila(df: pd.DataFrame, nombre: str) -> dict | None:
    if nombre == "Tierra":
        return TIERRA
    filas = df[df.planeta == nombre]
    return None if filas.empty else filas.iloc[0].to_dict()


def _veredicto(modelo, radio: float, luz: float, temp: float) -> None:
    if modelo is not None:
        prob = calculos.probabilidad(modelo, radio, luz, temp)
        st.metric("Según el modelo", "Habitable" if prob >= 0.5 else "No habitable",
                  f"{prob:.0%} de seguridad en que es habitable", delta_color="off")
    regla = calculos.segun_regla(radio, luz)
    st.markdown(f"**Mi regla** (zona habitable del Sol): {TEXTO_REGLA[regla]}  \n"
                f"**ESI:** {calculos.esi(radio, luz):.3f}")


def _parecidos(df: pd.DataFrame, radio: float, luz: float, temp: float) -> None:
    distancia = ((np.log10(df.insolacion_tierras.clip(lower=1e-4)) - np.log10(luz)) ** 2
                 + (np.log10(df.radio_tierras) - np.log10(radio)) ** 2
                 + ((df.temp_estrella_k.fillna(5778) - temp) / 1000) ** 2)
    cercanos = df.assign(distancia=distancia).nsmallest(5, "distancia")
    st.markdown("**Planetas reales más parecidos** (click para traerlo al simulador)")
    for columna, (_, planeta) in zip(st.columns(5), cercanos.iterrows()):
        columna.button(planeta.planeta, key=f"parecido_{planeta.planeta}", on_click=cargar, args=(planeta.to_dict(),),
                       help=f"ESI {planeta.esi:.3f} · estrella de {planeta.temp_estrella_k:,.0f} K",
                       use_container_width=True)


def vista(df: pd.DataFrame, modelo) -> None:
    st.markdown("Arma un planeta, o trae uno real desde el mapa, y mueve sus valores para ver qué diría el modelo. "
                "El modelo aprendió del criterio de los expertos de la UPR con los planetas que ellos sí evaluaron.")
    for columna, nombre in zip(st.columns(len(PRESETS)), PRESETS):
        fila = _fila(df, nombre)
        if fila is not None:
            columna.button(nombre, key=f"preset_{nombre}", on_click=cargar, args=(fila,), use_container_width=True)

    controles, mapa = st.columns([2, 3])
    with controles:
        st.subheader(st.session_state["sim_nombre"])
        radio = st.slider("Radio (Tierra = 1)", calculos.RADIO_MIN, calculos.RADIO_MAX, step=0.01, key="sim_radio",
                          on_change=_inventado)
        luz = st.select_slider("Luz que recibe (Tierra = 1)", options=OPCIONES_LUZ, key="sim_luz",
                               on_change=_inventado, format_func=lambda v: f"{v:.2f}")
        temp = st.slider("Temperatura de la estrella (K)", 2500, 7000, step=10, key="sim_temp", on_change=_inventado,
                         help="El Sol tiene 5,778 K. Las enanas rojas, menos de 4,000 K.")
        _veredicto(modelo, radio, luz, temp)
    with mapa:
        if modelo is None:
            st.info("El modelo no está disponible en este momento. El veredicto de mi regla y el ESI sí funcionan.")
        else:
            luz_grilla, radio_grilla, prob = calculos.grilla(modelo, temp)
            parecidos = df[(df.temp_estrella_k - temp).abs() <= 400]
            st.plotly_chart(graficas.mapa_modelo(luz_grilla, radio_grilla, prob, parecidos, (luz, radio)),
                            use_container_width=True)
            st.caption("Lo verde es donde el modelo considera habitable un planeta alrededor de esta estrella. "
                       "Mueve la temperatura de la estrella: con una enana roja, la zona se corre hacia planetas "
                       "que reciben menos luz. Los puntos grises son planetas reales con estrellas parecidas.")
            st.caption("Ojo: el modelo solo sabe lo que vio. Casi no hay planetas del tamaño de la Tierra alrededor de "
                       "estrellas como el Sol (son los más difíciles de detectar), así que ahí duda más: "
                       "la misma Tierra no le sale al 100%.")
    _parecidos(df, radio, luz, temp)
