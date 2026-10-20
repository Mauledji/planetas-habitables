"""Las dos gráficas de la app: el mapa de planetas reales y el mapa del modelo en el simulador."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

import estilos
from calculos import LUZ_MAX, LUZ_MIN, RADIO_MAX, RADIO_ROCOSO, ZONA_CONSERVADORA, ZONA_OPTIMISTA

MARCAS_LUZ = [4, 2, 1, 0.5, 0.25, 0.1, 0.05]
CONFIG = {"displayModeBar": False}
# Color de cada punto según la temperatura de su estrella: de enana roja a estrella blanco azulada
COLOR_ESTRELLA = [[0.0, "#FF5A36"], [0.22, "#FF8A4C"], [0.45, "#FFC47A"], [0.62, "#FFE9C4"],
                  [0.8, "#F4F6FF"], [1.0, "#AFC6FF"]]
TEMP_MIN, TEMP_MAX = 2500, 7500
EJE = dict(gridcolor="rgba(140, 154, 179, 0.08)", zeroline=False, showline=True, linecolor=estilos.LINEA,
           tickfont=dict(family=estilos.MONO, size=11, color=estilos.TENUE), automargin=True, title_standoff=12,
           title_font=dict(size=12, color=estilos.TENUE))


def _ejes(fig: go.Figure, alto: int) -> go.Figure:
    # En ejes logarítmicos Plotly usa log10 para el rango; más luz a la izquierda, como en los catálogos de exoplanetas
    fig.update_xaxes(type="log", range=[np.log10(LUZ_MAX * 1.1), np.log10(LUZ_MIN * 0.95)], tickvals=MARCAS_LUZ,
                     ticktext=[f"{m:g}" for m in MARCAS_LUZ], title="Luz que recibe (Tierra = 1)", **EJE)
    fig.update_yaxes(range=[0, RADIO_MAX + 0.1], title="Radio (Tierra = 1)", **EJE)
    fig.update_layout(
        height=alto, showlegend=False, margin=dict(l=8, r=8, t=40, b=8), clickmode="event+select",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=estilos.FUENTE, color=estilos.TENUE, size=12),
        hoverlabel=dict(bgcolor=estilos.SUPERFICIE, bordercolor=estilos.LINEA_FUERTE,
                        font=dict(family=estilos.MONO, size=12, color=estilos.TEXTO)),
    )
    return fig


def _etiqueta(fig: go.Figure, x: float, texto: str, color: str, y: float = 1.0, yref: str = "paper") -> None:
    # Las etiquetas van a mano: en ejes logarítmicos su posición x se da en log10
    fig.add_annotation(x=np.log10(x), y=y, yref=yref, yanchor="bottom", text=texto, showarrow=False,
                       font=dict(family=estilos.MONO, size=10, color=color))


def _tierra(fig: go.Figure) -> None:
    fig.add_trace(go.Scatter(x=[1], y=[1], mode="markers+text", text=["Tierra"], textposition="bottom center",
                             textfont=dict(family=estilos.MONO, size=11, color=estilos.FRIO), hoverinfo="skip",
                             marker=dict(size=13, color="#4C9BE8", line=dict(color="#CFEFFF", width=2))))


def _anillo(fig: go.Figure, x: float, y: float, nombre: str | None = None) -> None:
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="markers+text" if nombre else "markers", text=[nombre or ""], textposition="top center",
        textfont=dict(family=estilos.FUENTE, size=12, color=estilos.TEXTO), hoverinfo="skip",
        marker=dict(size=24, color="rgba(122, 162, 255, 0.14)", line=dict(color=estilos.ACENTO, width=2))))


def mapa_planetas(df: pd.DataFrame, seleccionado: str | None) -> go.Figure:
    """Planetas reales con el color de su estrella. Cada punto se puede clickear para abrir su ficha."""
    vista = df[(df.radio_tierras <= RADIO_MAX) & df.insolacion_tierras.between(LUZ_MIN, LUZ_MAX)]
    fig = go.Figure()
    fig.add_vrect(x0=ZONA_OPTIMISTA[0], x1=ZONA_OPTIMISTA[1], fillcolor=estilos.HABITABLE, opacity=0.05,
                  line_width=0, layer="below")
    fig.add_vrect(x0=ZONA_CONSERVADORA[0], x1=ZONA_CONSERVADORA[1], fillcolor=estilos.HABITABLE, opacity=0.1,
                  line_width=0, layer="below")
    _etiqueta(fig, 0.63, "ZONA HABITABLE", estilos.HABITABLE)
    _etiqueta(fig, 1.42, "optimista", "#8FD9B6")
    fig.add_hline(y=RADIO_ROCOSO, line_dash="dot", line_color=estilos.APAGADO, line_width=1)
    _etiqueta(fig, 0.085, "hasta aquí, rocosos", estilos.APAGADO, y=RADIO_ROCOSO, yref="y")

    temperatura = vista.temp_estrella_k
    texto_estrella = temperatura.map(lambda t: f"estrella de {t:,.0f} K" if pd.notna(t) else "estrella sin dato")
    fig.add_trace(go.Scatter(
        x=vista.insolacion_tierras, y=vista.radio_tierras, mode="markers",
        customdata=np.column_stack([vista.planeta, texto_estrella, vista.esi]),
        marker=dict(size=7, color=temperatura.fillna(5778).clip(TEMP_MIN, TEMP_MAX), colorscale=COLOR_ESTRELLA,
                    cmin=TEMP_MIN, cmax=TEMP_MAX, opacity=0.85, line=dict(width=0)),
        hovertemplate="<b>%{customdata[0]}</b><br>luz %{x:.2f} · radio %{y:.2f}<br>%{customdata[1]}"
                      "<br>ESI %{customdata[2]:.3f}<extra></extra>",
    ))
    _tierra(fig)
    if seleccionado in set(vista.planeta):
        p = vista[vista.planeta == seleccionado].iloc[0]
        _anillo(fig, p.insolacion_tierras, p.radio_tierras, seleccionado)
    return _ejes(fig, 540)


def mapa_modelo(luz, radio, prob, planetas_parecidos: pd.DataFrame, punto: tuple[float, float]) -> go.Figure:
    """Dónde considera habitable el modelo un planeta, para la estrella elegida en el simulador."""
    fig = go.Figure(go.Heatmap(
        x=luz, y=radio, z=prob, zmin=0, zmax=1, zsmooth="best",
        colorscale=[[0, "rgba(177, 151, 252, 0)"], [0.5, "rgba(177, 151, 252, 0.08)"],
                    [1, "rgba(177, 151, 252, 0.4)"]],
        colorbar=dict(title=dict(text="modelo", font=dict(family=estilos.MONO, size=10)), tickformat=".0%",
                      thickness=8, len=0.55, outlinewidth=0, tickfont=dict(family=estilos.MONO, size=10)),
        hovertemplate="luz %{x:.2f} · radio %{y:.2f}<br>habitable según el modelo: %{z:.0%}<extra></extra>",
    ))
    # La frontera donde el modelo pasa de "no" a "sí" (50%)
    fig.add_trace(go.Contour(x=luz, y=radio, z=prob, showscale=False, hoverinfo="skip", line_smoothing=1.1,
                             contours=dict(start=0.5, end=0.5, size=0.5, coloring="lines"),
                             line=dict(color=estilos.MODELO, width=2), colorscale=[[0, estilos.MODELO],
                                                                                   [1, estilos.MODELO]]))
    for borde in ZONA_CONSERVADORA:
        fig.add_vline(x=borde, line_dash="dash", line_color=estilos.HABITABLE, line_width=1, opacity=0.55)
    _etiqueta(fig, 0.63, "ZONA DE MI REGLA", estilos.HABITABLE)
    fig.add_trace(go.Scatter(x=planetas_parecidos.insolacion_tierras, y=planetas_parecidos.radio_tierras,
                             mode="markers", text=planetas_parecidos.planeta,
                             marker=dict(size=6, color="rgba(232, 238, 248, 0.45)", line=dict(width=0)),
                             hovertemplate="<b>%{text}</b><extra>planeta real</extra>"))
    _tierra(fig)
    _anillo(fig, punto[0], punto[1])
    return _ejes(fig, 470)
