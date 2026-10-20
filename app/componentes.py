"""Piezas de HTML que se repiten en la app. Todo texto que viene de los datos pasa por escape()."""
from html import escape

import streamlit as st

REPO = "https://github.com/Mauledji/planetas-habitables"


def encabezado(ceja: str, titulo: str, texto: str, principal: bool = False) -> None:
    clase = "titular" if principal else "titulo-pagina"
    st.html(f'<p class="ceja">{escape(ceja)}</p><h1 class="{clase}">{escape(titulo)}</h1>'
            f'<p class="entrada">{escape(texto)}</p>')


def franja(datos: list[tuple[str, str, str]]) -> None:
    """Fila de métricas tipo instrumento: (valor, nombre, tono) con tono '', 'habitable', 'modelo' o 'acento'."""
    celdas = "".join(
        f'<div class="dato"><span class="dato__valor">{escape(valor)}</span>'
        f'<span class="dato__nombre"><span class="punto punto--{tono or "neutro"}"></span>{escape(nombre)}</span></div>'
        for valor, nombre, tono in datos
    )
    st.html(f'<div class="franja">{celdas}</div>')


def seccion(titulo: str, detalle: str = "") -> None:
    st.html(f'<div class="seccion"><h3>{escape(titulo)}</h3><span>{escape(detalle)}</span></div>')


def esfera(tipo: str, tam: int = 72) -> str:
    return f'<div class="esfera esfera--{escape(tipo)}" style="--tam: {int(tam)}px"></div>'


def chip(texto: str, tono: str = "") -> str:
    clase = f"chip chip--{tono}" if tono else "chip"
    return f'<span class="{clase}">{escape(texto)}</span>'


def porcentaje(probabilidad: float) -> str:
    """Sin redondear a 0% o 100%: el modelo nunca está del todo seguro."""
    if probabilidad < 0.005:
        return "<1%"
    return ">99%" if probabilidad >= 0.995 else f"{probabilidad:.0%}"


def barra(probabilidad: float) -> str:
    ancho = max(0.0, min(1.0, float(probabilidad))) * 100
    return f'<div class="barra"><span style="width: {ancho:.1f}%"></span></div>'


def datos_grid(pares: list[tuple[str, str]]) -> str:
    celdas = "".join(f"<div><dt>{escape(nombre)}</dt><dd>{escape(valor)}</dd></div>" for nombre, valor in pares)
    return f'<dl class="datos-grid">{celdas}</dl>'


def pie() -> None:
    st.html(
        '<div class="pie"><span>Datos: <a href="https://exoplanetarchive.ipac.caltech.edu/" target="_blank">'
        'NASA Exoplanet Archive</a> · <a href="https://phl.upr.edu/hwc" target="_blank">Habitable Worlds Catalog'
        '</a> (PHL @ UPR Arecibo)</span>'
        f'<span>Proyecto final · Módulo 4 · <a href="{REPO}" target="_blank">código en GitHub</a></span></div>'
    )
