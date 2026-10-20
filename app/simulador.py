"""El sandbox: traer un planeta (real o inventado), cambiarle valores y ver qué dice el modelo."""
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

import calculos
import componentes as c
import graficas

OPCIONES_LUZ = [round(float(v), 3) for v in np.logspace(np.log10(calculos.LUZ_MIN), np.log10(calculos.LUZ_MAX), 121)]
TIERRA = {"planeta": "Tierra", "radio_tierras": 1.0, "insolacion_tierras": 1.0, "temp_estrella_k": 5778}
PRESETS = ["Tierra", "TRAPPIST-1 e", "Teegarden's Star b", "Kepler-452 b", "Gliese 48 b"]
TEXTO_REGLA = {"conservador": "Habitable (conservador)", "optimista": "Habitable (optimista)", "no": "No habitable"}
TAM_TIERRA = 46


def _poner(planeta: dict) -> None:
    luz = max(float(planeta["insolacion_tierras"]), 1e-6)
    temp = planeta.get("temp_estrella_k")
    temp = 5778 if temp is None or pd.isna(temp) else float(temp)
    st.session_state["sim_nombre"] = planeta["planeta"]
    st.session_state["sim_radio"] = float(np.clip(round(planeta["radio_tierras"], 2), calculos.RADIO_MIN,
                                                  calculos.RADIO_MAX))
    st.session_state["sim_luz"] = min(OPCIONES_LUZ, key=lambda o: abs(np.log10(o) - np.log10(luz)))
    st.session_state["sim_temp"] = int(np.clip(round(temp / 10) * 10, 2500, 7000))


def cargar(planeta: dict) -> None:
    """Callback: pone los datos de un planeta en los controles y pide abrir el simulador."""
    _poner(planeta)
    st.session_state["ir_a"] = "experimentar"


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


def _presets(df: pd.DataFrame) -> None:
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        st.html('<span class="ceja" style="margin:0">Probar con</span>', width="content")
        for nombre in PRESETS:
            fila = _fila(df, nombre)
            if fila is not None:
                st.button(nombre, key=f"preset_{nombre}", on_click=_poner, args=(fila,), type="secondary")


def _tamanos(radio: float, tipo: str) -> str:
    """La Tierra y el planeta lado a lado, a escala (con un límite para que quepan)."""
    tam = int(np.clip(TAM_TIERRA * radio, 14, 150))
    return (f'<div class="tamanos"><figure>{c.esfera("templado", TAM_TIERRA)}<figcaption>Tierra</figcaption></figure>'
            f'<figure>{c.esfera(tipo, tam)}<figcaption>{radio:.2f} ×</figcaption></figure></div>')


def _controles() -> tuple[float, float, float]:
    radio, luz = st.session_state["sim_radio"], st.session_state["sim_luz"]
    tipo = calculos.aspecto(radio, luz)
    with st.container(key="simulador"):
        st.html(f'<p class="ceja">Tu planeta</p><h3 class="sim-nombre">{escape(st.session_state["sim_nombre"])}</h3>'
                f'<p class="ficha-sub">{escape(calculos.ASPECTOS[tipo])} <span class="tenue">· ilustración</span></p>'
                + _tamanos(radio, tipo))
        radio = st.slider(":material/straighten: Radio (Tierra = 1)", calculos.RADIO_MIN, calculos.RADIO_MAX,
                          step=0.01, key="sim_radio", on_change=_inventado, persist_state="session")
        luz = st.select_slider(":material/light_mode: Luz que recibe (Tierra = 1)", options=OPCIONES_LUZ,
                               key="sim_luz", on_change=_inventado, format_func=lambda v: f"{v:.2f}",
                               persist_state="session")
        temp = st.slider(":material/thermostat: Temperatura de la estrella (K)", 2500, 7000, step=10, key="sim_temp",
                         on_change=_inventado, persist_state="session",
                         help="El Sol tiene 5,778 K. Las enanas rojas, menos de 4,000 K.")
    return radio, luz, temp


def _veredicto(modelo, radio: float, luz: float, temp: float) -> None:
    regla = calculos.segun_regla(radio, luz)
    temp_planeta = calculos.temperatura_equilibrio(luz)
    with st.container(key="veredicto"):
        if modelo is None:
            st.html('<p class="ceja">Veredicto del modelo</p><p class="tenue">El modelo no está disponible en este '
                    'momento. Mi regla y el ESI sí funcionan.</p>')
            prob = None
        else:
            prob = calculos.probabilidad(modelo, radio, luz, temp)
            habitable = prob >= 0.5
            coinciden = habitable == (regla != "no")
            st.html(
                '<p class="ceja">Veredicto del modelo</p>'
                f'<div class="veredicto"><span class="veredicto__numero">{escape(c.porcentaje(prob))}</span>'
                f'<span class="veredicto__texto">de seguridad en que es habitable<strong>'
                f'{"Habitable" if habitable else "No habitable"}</strong></span></div>'
                + c.barra(prob)
                + '<div class="chips" style="margin-top:1rem">'
                + c.chip("El modelo y mi regla coinciden" if coinciden else "El modelo y mi regla no coinciden",
                         "habitable" if coinciden else "caliente")
                + "</div>"
            )
        st.html(c.datos_grid([
            ("Mi regla (zona del Sol)", TEXTO_REGLA[regla]),
            ("Parecido a la Tierra (ESI)", f"{calculos.esi(radio, luz):.3f}"),
            ("Temperatura estimada", f"{temp_planeta:,.0f} K ({temp_planeta - 273.15:,.0f} °C)"),
        ]) + '<p class="nota">Mi regla usa la zona habitable de una estrella como el Sol. El modelo aprendió de los '
             'expertos que esa zona se corre según la temperatura de la estrella.</p>')


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
                'estrella. Baja la temperatura de la estrella: con una enana roja, la zona se corre hacia planetas que '
                'reciben menos luz. Ojo: casi no hay planetas del tamaño de la Tierra alrededor de estrellas como el '
                'Sol (son los más difíciles de detectar), así que ahí el modelo duda más y la misma Tierra no le sale '
                'al 100%.</p>')


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
                 "Arma un planeta o trae uno real, mueve sus valores y mira qué diría el modelo. Aprendió del "
                 "criterio de los expertos de la UPR con los planetas que ellos sí evaluaron.")
    _presets(df)
    izquierda, derecha = st.columns([5, 7], gap="large")
    with izquierda:
        radio, luz, temp = _controles()
    with derecha:
        _veredicto(modelo, radio, luz, temp)
    _mapa(df, modelo, radio, luz, temp)
    _parecidos(df, radio, luz, temp)
