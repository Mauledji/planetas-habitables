"""Las dos gráficas de la app: el mapa de planetas reales y el mapa del modelo en el simulador."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from calculos import LUZ_MAX, LUZ_MIN, RADIO_MAX, ZONA_CONSERVADORA, ZONA_OPTIMISTA

ROSADO, CELESTE = "#f472b6", "#38bdf8"
MARCAS_LUZ = [4, 2, 1, 0.5, 0.25, 0.1, 0.05]


def _ejes(fig: go.Figure, alto: int) -> go.Figure:
    # En ejes logarítmicos Plotly usa log10 para el rango; más luz a la izquierda, como en los catálogos de exoplanetas
    fig.update_xaxes(type="log", range=[np.log10(LUZ_MAX * 1.1), np.log10(LUZ_MIN * 0.95)],
                     tickvals=MARCAS_LUZ, ticktext=[str(m) for m in MARCAS_LUZ], title="Luz que recibe (Tierra = 1)")
    fig.update_yaxes(range=[0, RADIO_MAX + 0.1], title="Radio (Tierra = 1)")
    fig.update_layout(height=alto, showlegend=False, template="plotly_dark", margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", clickmode="event+select")
    return fig


def _tierra(fig: go.Figure) -> None:
    fig.add_trace(go.Scatter(x=[1], y=[1], mode="markers+text", text=["Tierra"], textposition="top center",
                             marker=dict(size=18, color=CELESTE, symbol="star"), hoverinfo="skip"))


def mapa_planetas(df: pd.DataFrame, seleccionado: str | None) -> go.Figure:
    """Planetas reales coloreados por ESI. Cada punto se puede clickear para abrir su ficha."""
    vista = df[(df.radio_tierras <= RADIO_MAX) & df.insolacion_tierras.between(LUZ_MIN, LUZ_MAX)]
    fig = go.Figure()
    fig.add_vrect(x0=ZONA_OPTIMISTA[0], x1=ZONA_OPTIMISTA[1], fillcolor="#facc15", opacity=0.08, line_width=0)
    fig.add_vrect(x0=ZONA_CONSERVADORA[0], x1=ZONA_CONSERVADORA[1], fillcolor="#22c55e", opacity=0.14, line_width=0)
    # Las etiquetas van a mano: en ejes logarítmicos su posición x se da en log10
    for texto, x, color in [("zona habitable<br>conservadora", 0.63, "#4ade80"), ("optimista", 1.42, "#fde047")]:
        fig.add_annotation(x=np.log10(x), y=1, yref="paper", yanchor="bottom", text=texto, showarrow=False,
                           font=dict(size=11, color=color))
    fig.add_hline(y=1.6, line_dash="dot", line_color="#94a3b8")
    fig.add_annotation(x=np.log10(0.08), y=1.6, text="hasta aquí, rocosos", showarrow=False, yanchor="bottom",
                       font=dict(size=10, color="#94a3b8"))
    fig.add_trace(go.Scatter(
        x=vista.insolacion_tierras, y=vista.radio_tierras, mode="markers", customdata=vista.planeta,
        marker=dict(size=8, color=vista.esi, colorscale="Viridis", cmin=0, cmax=1, opacity=0.85,
                    colorbar=dict(title="ESI")),
        hovertemplate="<b>%{customdata}</b><br>Luz: %{x:.2f}<br>Radio: %{y:.2f}<extra>click para ver</extra>",
    ))
    if seleccionado in set(vista.planeta):
        p = vista[vista.planeta == seleccionado].iloc[0]
        fig.add_trace(go.Scatter(x=[p.insolacion_tierras], y=[p.radio_tierras], mode="markers", hoverinfo="skip",
                                 marker=dict(size=20, color="rgba(0,0,0,0)", line=dict(color=ROSADO, width=3))))
    _tierra(fig)
    return _ejes(fig, 520)


def mapa_modelo(luz, radio, prob, planetas_parecidos: pd.DataFrame, punto: tuple[float, float]) -> go.Figure:
    """Dónde considera habitable el modelo un planeta, para la estrella elegida en el simulador."""
    fig = go.Figure(go.Heatmap(
        x=luz, y=radio, z=prob, zmin=0, zmax=1, zsmooth="best",
        colorscale=[[0, "rgba(7,11,26,0)"], [0.5, "#1f6f5c"], [1, "#4ade80"]],
        colorbar=dict(title="Habitable<br>según el<br>modelo", tickformat=".0%"),
        hovertemplate="Luz %{x:.2f} · Radio %{y:.2f}<br>Habitable: %{z:.0%}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(x=planetas_parecidos.insolacion_tierras, y=planetas_parecidos.radio_tierras,
                             mode="markers", text=planetas_parecidos.planeta, marker=dict(size=6, color="#cbd5e1"),
                             hovertemplate="<b>%{text}</b><extra>planeta real</extra>"))
    _tierra(fig)
    fig.add_trace(go.Scatter(x=[punto[0]], y=[punto[1]], mode="markers", hoverinfo="skip",
                             marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=ROSADO, width=3))))
    return _ejes(fig, 460)
