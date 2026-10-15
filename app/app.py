"""¿Hay otra Tierra? Buscador de planetas potencialmente habitables."""
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import datos

st.set_page_config(page_title="¿Hay otra Tierra?", page_icon="🪐", layout="wide")

REPO = "https://github.com/Mauledji/planetas-habitables"
ANIOS_VOYAGER_POR_ANIO_LUZ = 17_600  # la Voyager 1 viaja a unos 17 km/s

COLUMNAS_TABLA = {
    "planeta": st.column_config.TextColumn("Planeta"),
    "esi": st.column_config.ProgressColumn("Parecido a la Tierra (ESI)", min_value=0, max_value=1, format="%.3f"),
    "potencialmente_habitable": st.column_config.TextColumn("Habitable"),
    "radio_tierras": st.column_config.NumberColumn("Radio (Tierra = 1)", format="%.2f"),
    "insolacion_tierras": st.column_config.NumberColumn("Luz que recibe (Tierra = 1)", format="%.2f"),
    "distancia_anios_luz": st.column_config.NumberColumn("Años luz", format="%.0f"),
    "estrella": st.column_config.TextColumn("Estrella"),
    "anio_descubrimiento": st.column_config.NumberColumn("Descubierto", format="%d"),
    "evaluado_por_expertos": st.column_config.CheckboxColumn("En el catálogo de la UPR"),
}


def cargar() -> pd.DataFrame:
    try:
        df = datos.catalogo()
    except Exception as error:  # se muestra un mensaje simple y el detalle queda en los logs de la app
        print(f"Error leyendo gold: {error!r}", file=sys.stderr, flush=True)
        st.error("No pude leer el catálogo de planetas. Revisa que el SQL warehouse esté encendido y vuelve a cargar.")
        st.stop()
    return df.assign(evaluado_por_expertos=df.evaluado_por_expertos.fillna(False).astype(bool))


def encabezado(df: pd.DataFrame) -> None:
    st.title("🪐 ¿Hay otra Tierra?")
    st.caption("Los planetas confirmados que más se parecen a la Tierra, con datos de la NASA Exoplanet Archive "
               "y del Habitable Worlds Catalog (PHL @ UPR Arecibo).")
    habitables = df[df.potencialmente_habitable != "no"]
    nuevos = habitables[~habitables.evaluado_por_expertos]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planetas evaluados", f"{len(df):,}")
    c2.metric("Potencialmente habitables", f"{len(habitables):,}")
    c3.metric("Habitables nuevos, sin evaluar por expertos", f"{len(nuevos):,}")
    c4.metric("Datos actualizados", pd.to_datetime(df.actualizado.max()).strftime("%d/%m/%Y"))


def filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")
    solo_habitables = st.sidebar.toggle("Solo potencialmente habitables", value=True)
    radio = st.sidebar.slider("Radio (Tierra = 1)", 0.0, 6.0, (0.0, 6.0), 0.1)
    luz = st.sidebar.slider("Luz que recibe (Tierra = 1)", 0.0, 5.0, (0.0, 5.0), 0.05)
    distancia = st.sidebar.slider("Distancia máxima (años luz)", 10, 5000, 5000, 10)
    metodos = st.sidebar.multiselect("Método de descubrimiento", sorted(df.metodo_descubrimiento.dropna().unique()))

    filtrado = df[df.radio_tierras.between(*radio) & df.insolacion_tierras.between(*luz)]
    filtrado = filtrado[filtrado.distancia_anios_luz.isna() | (filtrado.distancia_anios_luz <= distancia)]
    if solo_habitables:
        filtrado = filtrado[filtrado.potencialmente_habitable != "no"]
    if metodos:
        filtrado = filtrado[filtrado.metodo_descubrimiento.isin(metodos)]
    return filtrado.sort_values("esi", ascending=False)


def tabla(df: pd.DataFrame) -> None:
    st.dataframe(df[list(COLUMNAS_TABLA)], column_config=COLUMNAS_TABLA, hide_index=True, use_container_width=True)


def mapa(df: pd.DataFrame) -> None:
    st.markdown("Cada punto es un planeta. A la izquierda reciben más luz que la Tierra, a la derecha menos. "
                "Las franjas son la **zona habitable**: la distancia a su estrella donde podría haber agua líquida.")
    vista = df[(df.radio_tierras <= 4) & (df.insolacion_tierras.between(0.05, 4))]
    fig = go.Figure()
    fig.add_vrect(x0=0.32, x1=1.776, fillcolor="#facc15", opacity=0.08, line_width=0,
                  annotation_text="zona optimista", annotation_position="top left")
    fig.add_vrect(x0=0.356, x1=1.107, fillcolor="#22c55e", opacity=0.14, line_width=0,
                  annotation_text="zona conservadora", annotation_position="bottom right")
    fig.add_hline(y=1.6, line_dash="dot", line_color="#94a3b8", annotation_text="hasta aquí, rocosos")
    fig.add_trace(go.Scatter(
        x=vista.insolacion_tierras, y=vista.radio_tierras, mode="markers", text=vista.planeta,
        customdata=vista[["esi"]],
        marker=dict(size=7, color=vista.esi, colorscale="Viridis", cmin=0, cmax=1, opacity=0.85,
                    colorbar=dict(title="ESI")),
        hovertemplate="<b>%{text}</b><br>Luz: %{x:.2f}<br>Radio: %{y:.2f}<br>ESI: %{customdata[0]:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(x=[1], y=[1], mode="markers+text", text=["Tierra"], textposition="top center",
                             marker=dict(size=18, color="#38bdf8", symbol="star"), hoverinfo="skip"))
    fig.update_xaxes(type="log", autorange="reversed", title="Luz que recibe (Tierra = 1)")
    fig.update_yaxes(title="Radio (Tierra = 1)")
    fig.update_layout(height=560, showlegend=False, template="plotly_dark",
                      margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def ficha(df: pd.DataFrame) -> None:
    nombres = df.sort_values("esi", ascending=False).planeta.tolist()
    planeta = st.selectbox("Busca un planeta", nombres, index=0)
    p = df[df.planeta == planeta].iloc[0]

    st.subheader(planeta)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parecido a la Tierra (ESI)", f"{p.esi:.3f}",
              help=None if pd.isna(p.esi_expertos) else f"Según los expertos de la UPR: {p.esi_expertos:.3f}")
    c2.metric("Radio", f"{p.radio_tierras:.2f} Tierras", help=f"De dónde sale: {p.fuente_radio}")
    c3.metric("Luz que recibe", f"{p.insolacion_tierras:.2f} Tierras", help=f"De dónde sale: {p.fuente_insolacion}")
    if pd.isna(p.distancia_anios_luz):
        c4.metric("Distancia", "desconocida")
    else:
        c4.metric("Distancia", f"{p.distancia_anios_luz:,.0f} años luz",
                  help=f"La Voyager 1 tardaría unos {p.distancia_anios_luz * ANIOS_VOYAGER_POR_ANIO_LUZ:,.0f} años en llegar")

    habitable = {"conservador": "sí (criterio conservador)", "optimista": "sí (criterio optimista)"}
    st.markdown(
        f"- Orbita la estrella **{p.estrella}**"
        f"{'' if pd.isna(p.tipo_espectral) else f' (tipo {p.tipo_espectral})'}.\n"
        f"- Descubierto en **{p.anio_descubrimiento}** por **{p.metodo_descubrimiento}** desde **{p.instalacion}**.\n"
        f"- ¿Potencialmente habitable? **{habitable.get(p.potencialmente_habitable, 'no')}**. "
        f"Tamaño: {p.tamano}, zona habitable: {p.zona_habitable}.\n"
        f"- {'Está en el catálogo de expertos de la UPR.' if p.evaluado_por_expertos else 'Todavía no está en el catálogo de expertos de la UPR: esta evaluación la hace el proyecto.'}"
    )

    historial = datos.historial(planeta)
    st.markdown(f"**{len(historial)} mediciones publicadas de este planeta**")
    st.dataframe(historial, hide_index=True, use_container_width=True, column_config={
        "fecha_publicacion": st.column_config.DateColumn("Publicado"),
        "referencia": st.column_config.TextColumn("Artículo"),
        "link_referencia": st.column_config.LinkColumn("Link", display_text="abrir"),
        "es_oficial": st.column_config.CheckboxColumn("Oficial"),
        "radio_tierras": st.column_config.NumberColumn("Radio", format="%.2f"),
        "masa_tierras": st.column_config.NumberColumn("Masa", format="%.2f"),
        "insolacion_tierras": st.column_config.NumberColumn("Luz", format="%.2f"),
        "temp_equilibrio_k": st.column_config.NumberColumn("Temp. (K)", format="%.0f"),
        "periodo_dias": st.column_config.NumberColumn("Año (días)", format="%.1f"),
    })


def nuevos(df: pd.DataFrame) -> None:
    st.markdown("El catálogo de habitabilidad de la Universidad de Puerto Rico se actualizó por última vez en "
                "marzo de 2024. Estos planetas **no están en él**: su habitabilidad la calcula este proyecto con "
                "los datos de la NASA.")
    tabla(df[~df.evaluado_por_expertos & (df.potencialmente_habitable != "no")].sort_values("esi", ascending=False))


def como_funciona() -> None:
    st.markdown(f"""
**De dónde salen los datos**
- [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/): todas las mediciones publicadas de cada planeta confirmado.
- [Habitable Worlds Catalog](https://phl.upr.edu/hwc), PHL @ UPR Arecibo: la evaluación de habitabilidad de los expertos.

**Cómo se procesan (Databricks)**
1. **Bronze:** los lotes nuevos de la NASA llegan a un volume y Auto Loader carga solo los archivos nuevos.
2. **Silver:** se dejan los tipos correctos, un registro por planeta y se completan los datos que faltan con reglas explicables.
3. **Gold:** se calcula el ESI (índice de parecido a la Tierra) y si está en la zona habitable.
4. Unity Catalog decide quién ve qué: los planetas cuya existencia la NASA tiene en disputa no se publican aquí.

**ESI**: `1 − √(½·[((S−1)/(S+1))² + ((R−1)/(R+1))²])`, con S = luz que recibe y R = radio, comparados con la Tierra.

Código: [{REPO}]({REPO})
""")


df = cargar()
encabezado(df)
filtrado = filtros(df)

buscador, mapa_tab, ficha_tab, nuevos_tab, info = st.tabs(
    ["🔭 Buscador", "🌡️ Mapa de habitabilidad", "🪐 Ficha del planeta", "🆕 Nuevos descubrimientos", "ℹ️ Cómo funciona"])
with buscador:
    st.caption(f"{len(filtrado):,} planetas con estos filtros, ordenados por parecido a la Tierra")
    tabla(filtrado)
with mapa_tab:
    mapa(filtrado)
with ficha_tab:
    ficha(df)
with nuevos_tab:
    nuevos(df)
with info:
    como_funciona()
