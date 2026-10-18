"""¿Hay otra Tierra? Sandbox para explorar planetas reales y experimentar con el modelo de habitabilidad."""
import sys

import pandas as pd
import streamlit as st

import datos
import graficas
import simulador

st.set_page_config(page_title="¿Hay otra Tierra?", page_icon="🪐", layout="wide")

REPO = "https://github.com/Mauledji/planetas-habitables"
ANIOS_VOYAGER_POR_ANIO_LUZ = 17_600  # la Voyager 1 viaja a unos 17 km/s
VISTAS = ["🔭 Explorar", simulador.VISTA, "🆕 Nuevos descubrimientos", "ℹ️ Cómo funciona"]
HABITABLE = {"conservador": "sí (criterio conservador)", "optimista": "sí (criterio optimista)", "no": "no"}

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


def encabezado(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    st.title("🪐 ¿Hay otra Tierra?")
    st.caption("Planetas confirmados por la NASA, qué tanto se parecen a la Tierra y qué diría un modelo entrenado "
               "con el criterio de los expertos del Habitable Worlds Catalog (PHL @ UPR Arecibo).")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planetas evaluados", f"{len(df):,}")
    c2.metric("Potencialmente habitables (mi regla)", f"{(df.potencialmente_habitable != 'no').sum():,}")
    c3.metric("Nuevos, sin evaluar por expertos", f"{len(pred):,}")
    c4.metric("Habitables según el modelo (nuevos)", f"{int(pred.habitable_segun_modelo.sum()):,}")


def filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")
    solo_habitables = st.sidebar.toggle("Solo potencialmente habitables", value=False)
    radio = st.sidebar.slider("Radio (Tierra = 1)", 0.0, 6.0, (0.0, 6.0), 0.1)
    luz = st.sidebar.slider("Luz que recibe (Tierra = 1)", 0.0, 5.0, (0.0, 5.0), 0.05)
    distancia = st.sidebar.slider("Distancia máxima (años luz)", 10, 5000, 5000, 10)
    filtrado = df[df.radio_tierras.between(*radio) & df.insolacion_tierras.between(*luz)]
    filtrado = filtrado[filtrado.distancia_anios_luz.isna() | (filtrado.distancia_anios_luz <= distancia)]
    if solo_habitables:
        filtrado = filtrado[filtrado.potencialmente_habitable != "no"]
    return filtrado.sort_values("esi", ascending=False)


def _seleccionar(clave: str, nombre: str | None) -> bool:
    """Si un mapa o tabla tiene un click nuevo, ese planeta pasa a ser el seleccionado."""
    if nombre and st.session_state.get(f"_ultimo_{clave}") != nombre:
        st.session_state[f"_ultimo_{clave}"] = nombre
        st.session_state["planeta"] = nombre
        return True
    return False


def _click_en_mapa(evento) -> str | None:
    puntos = (evento or {}).get("selection", {}).get("points", [])
    if not puntos:
        return None
    dato = puntos[0].get("customdata")
    return dato[0] if isinstance(dato, list) else dato


def tabla(df: pd.DataFrame, clave: str, extra: dict | None = None) -> None:
    columnas = {**COLUMNAS_TABLA, **(extra or {})}
    evento = st.dataframe(df[list(columnas)], column_config=columnas, hide_index=True, use_container_width=True,
                          on_select="rerun", selection_mode="single-row", key=clave)
    filas = evento.selection.rows
    if filas and _seleccionar(clave, df.iloc[filas[0]].planeta):
        st.rerun()


def ficha(df: pd.DataFrame, pred: pd.DataFrame, nombre: str) -> None:
    filas = df[df.planeta == nombre]
    if filas.empty:
        st.info("Haz click en un planeta del mapa o de la tabla para ver su ficha.")
        return
    p = filas.iloc[0]
    st.subheader(nombre)
    c1, c2 = st.columns(2)
    c1.metric("Parecido a la Tierra (ESI)", f"{p.esi:.3f}")
    c2.metric("Distancia (años luz)", "?" if pd.isna(p.distancia_anios_luz) else f"{p.distancia_anios_luz:,.0f}",
              help=None if pd.isna(p.distancia_anios_luz)
              else f"La Voyager 1 tardaría unos {p.distancia_anios_luz * ANIOS_VOYAGER_POR_ANIO_LUZ:,.0f} años")
    if p.evaluado_por_expertos:
        segun = f"según los expertos de la UPR: **{HABITABLE.get(p.habitable_expertos, 'no')}**"
    else:
        prediccion = pred[pred.planeta == nombre]
        segun = ("según el modelo: **sí**" if not prediccion.empty and prediccion.iloc[0].habitable_segun_modelo
                 else "según el modelo: **no**") + " (los expertos todavía no lo evalúan)"
    st.markdown(
        f"- Radio **{p.radio_tierras:.2f}** Tierras ({p.fuente_radio}) · luz **{p.insolacion_tierras:.2f}** "
        f"({p.fuente_insolacion})\n"
        f"- Estrella **{p.estrella}**, de {p.temp_estrella_k:,.0f} K\n"
        f"- Descubierto en **{p.anio_descubrimiento}** por {p.metodo_descubrimiento} desde {p.instalacion}\n"
        f"- ¿Habitable? Mi regla: **{HABITABLE.get(p.potencialmente_habitable, 'no')}** · {segun}"
    )
    st.button("🧪 Experimentar con este planeta", on_click=simulador.cargar, args=(p.to_dict(),), type="primary")
    with st.expander("Sus mediciones publicadas"):
        st.dataframe(datos.historial(nombre), hide_index=True, use_container_width=True, column_config={
            "link_referencia": st.column_config.LinkColumn("Artículo", display_text="abrir"),
            "es_oficial": st.column_config.CheckboxColumn("Oficial"),
        })


def explorar(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    filtrado = filtros(df)
    mapa, detalle = st.columns([3, 2])
    with mapa:
        evento = st.plotly_chart(graficas.mapa_planetas(filtrado, st.session_state.get("planeta")),
                                 use_container_width=True, on_select="rerun", selection_mode="points", key="mapa")
        _seleccionar("mapa", _click_en_mapa(evento))
        st.caption("Cada punto es un planeta: haz click para ver su ficha. Las franjas son la zona habitable de una "
                   "estrella como el Sol.")
    with detalle:
        ficha(df, pred, st.session_state.get("planeta", ""))
    st.markdown(f"**{len(filtrado):,} planetas** con estos filtros, ordenados por parecido a la Tierra")
    tabla(filtrado, "tabla_explorar")


def nuevos(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    st.markdown("El catálogo de habitabilidad de la Universidad de Puerto Rico se actualizó por última vez en marzo "
                "de 2024. Estos planetas **no están en él**: los evalúan mi regla y el modelo de machine learning.")
    juntos = df.merge(pred[["planeta", "probabilidad"]], on="planeta").sort_values(["probabilidad", "esi"],
                                                                                   ascending=False)
    tabla(juntos, "tabla_nuevos", {"probabilidad": st.column_config.ProgressColumn(
        "Habitable según el modelo", min_value=0, max_value=1, format="%.2f")})
    ficha(df, pred, st.session_state.get("planeta", ""))


def como_funciona() -> None:
    st.markdown(f"""
**De dónde salen los datos**
- [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/): todas las mediciones publicadas de cada planeta confirmado.
- [Habitable Worlds Catalog](https://phl.upr.edu/hwc), PHL @ UPR Arecibo: la evaluación de habitabilidad de los expertos.

**Cómo se procesan (Databricks)**
1. **Bronze:** los lotes nuevos de la NASA llegan a un volume y Auto Loader carga solo los archivos nuevos.
2. **Silver:** tipos correctos, un registro por planeta y los datos que faltan completados con reglas explicables.
3. **Gold:** el ESI (parecido a la Tierra) y si el planeta está en la zona habitable de una estrella como el Sol.
4. **Machine learning:** un modelo (gradient boosting) aprende del criterio de los expertos con los planetas que ellos sí
   evaluaron y le gana a mi regla, porque aprende que la zona habitable cambia según la temperatura de la estrella.
   El modelo vive en MLflow; el job lo usa para evaluar los planetas nuevos y publica una copia en gold para este
   simulador (en Free Edition la app no puede bajar los archivos de MLflow).
5. Unity Catalog decide quién ve qué: los planetas que la NASA tiene en disputa no se publican aquí.

**ESI**: `1 − √(½·[((S−1)/(S+1))² + ((R−1)/(R+1))²])`, con S = luz que recibe y R = radio, comparados con la Tierra.

Código: [{REPO}]({REPO})
""")


df, pred, modelo = cargar()
simulador.iniciar()
st.session_state.setdefault("vista", VISTAS[0])
encabezado(df, pred)
vista = st.radio("Vista", VISTAS, horizontal=True, key="vista", label_visibility="collapsed")
if vista == VISTAS[0]:
    explorar(df, pred)
elif vista == simulador.VISTA:
    simulador.vista(df, modelo)
elif vista == VISTAS[2]:
    nuevos(df, pred)
else:
    como_funciona()
