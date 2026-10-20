"""¿Hay otra Tierra? Explorar planetas reales y experimentar con el modelo de habitabilidad."""
import sys

import pandas as pd
import streamlit as st

import como_funciona
import componentes
import datos
import estilos
import explorar
import nuevos
import simulador

LOGO = "assets/logo.svg"
st.set_page_config(page_title="¿Hay otra Tierra?", page_icon=LOGO, layout="wide", initial_sidebar_state="collapsed")


def cargar() -> tuple[pd.DataFrame, pd.DataFrame, object]:
    try:
        df, pred = datos.catalogo(), datos.predicciones()
    except Exception as error:  # mensaje simple en pantalla; el detalle queda en los logs de la app
        print(f"Error leyendo gold: {error!r}", file=sys.stderr, flush=True)
        st.error("No pude leer el catálogo de planetas. Revisa que el SQL warehouse esté encendido y vuelve a cargar.")
        st.stop()
    try:
        modelo = datos.modelo_actual(pred)
    except Exception as error:
        print(f"Error cargando el modelo: {error!r}", file=sys.stderr, flush=True)
        modelo = None
    df = df.assign(evaluado_por_expertos=df.evaluado_por_expertos.fillna(False).astype(bool))
    return df, pred, modelo


estilos.aplicar()
st.logo(LOGO, size="large")
df, pred, modelo = cargar()
simulador.iniciar()


def _explorar() -> None:
    explorar.pagina(df, pred)


def _experimentar() -> None:
    simulador.pagina(df, modelo)


def _nuevos() -> None:
    nuevos.pagina(df, pred)


def _como_funciona() -> None:
    como_funciona.pagina(df, pred)


PAGINAS = {
    "explorar": st.Page(_explorar, title="Explorar", icon=":material/travel_explore:", url_path="explorar",
                        default=True),
    "experimentar": st.Page(_experimentar, title="Experimentar", icon=":material/science:", url_path="experimentar"),
    "nuevos": st.Page(_nuevos, title="Nuevos descubrimientos", icon=":material/auto_awesome:", url_path="nuevos"),
    "como_funciona": st.Page(_como_funciona, title="Cómo funciona", icon=":material/account_tree:",
                             url_path="como-funciona"),
}
actual = st.navigation(list(PAGINAS.values()), position="top")
# Un botón "Experimentar con este planeta" deja pedido el cambio de página (los callbacks no pueden cambiarla)
destino = st.session_state.pop("ir_a", None)
if destino in PAGINAS:
    st.switch_page(PAGINAS[destino])
actual.run()
componentes.pie()
