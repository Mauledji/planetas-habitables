"""Cómo funciona: el recorrido de los datos, de la NASA a esta app, con los números reales de cada etapa."""
from html import escape
from urllib.parse import quote

import pandas as pd
import streamlit as st

import componentes as c
import estilos

TRAZOS = {
    "fuentes": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
               '<path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "bronze": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
    "silver": '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    "gold": '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 7 5-3 5 3-1.5-7"/>',
    "modelo": '<rect x="6" y="6" width="12" height="12" rx="2"/>'
              '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "app": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "gobernanza": '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "calidad": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "orquestacion": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
}


COLORES = {"fuentes": "#9DB8FF", "bronze": "#D9925E", "silver": "#C3CCDD", "gold": "#E9C46A",
           "modelo": estilos.MODELO, "app": estilos.HABITABLE}


def _icono(nombre: str, color: str) -> str:
    # st.html limpia los <svg> en línea, así que el ícono va como imagen (data URI)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{TRAZOS[nombre]}</svg>')
    return f'<img src="data:image/svg+xml;utf8,{quote(svg)}" alt="" aria-hidden="true">'


def _etapa(clase: str, capa: str, texto: str, dato: str) -> str:
    return (f'<div class="etapa etapa--{clase}"><div class="etapa__icono">{_icono(clase, COLORES[clase])}</div>'
            f'<p class="etapa__capa">{escape(capa)}</p><p class="etapa__texto">{escape(texto)}</p>'
            f'<p class="etapa__dato">{escape(dato)}</p></div>')


def _bloque(icono: str, titulo: str, texto: str) -> str:
    return (f'<div class="bloque"><div class="bloque__icono">{_icono(icono, estilos.ACENTO)}</div>'
            f'<h4>{escape(titulo)}</h4><p>{escape(texto)}</p></div>')


def pagina(df: pd.DataFrame, pred: pd.DataFrame) -> None:
    c.encabezado("Arquitectura", "Cómo funciona",
                 "Un pipeline en Databricks lleva las mediciones de la NASA por tres capas (bronze, silver y gold), "
                 "un modelo evalúa los planetas nuevos y Unity Catalog decide qué llega a esta app.")
    completados = int((df.fuente_radio != "medición oficial").sum() + (df.fuente_insolacion != "medición oficial").sum())
    st.html('<div class="flujo">' + "".join([
        _etapa("fuentes", "Fuentes", "NASA Exoplanet Archive y el catálogo de habitabilidad de la UPR.",
               "2 catálogos públicos"),
        _etapa("bronze", "Bronze", "Auto Loader carga solo los lotes nuevos que llegan al volume.",
               f"{int(df.mediciones.sum()):,} mediciones"),
        _etapa("silver", "Silver", "Un registro por planeta y los datos faltantes completados con reglas.",
               f"{completados:,} datos completados"),
        _etapa("gold", "Gold", "El ESI y la zona habitable, con reglas de calidad que no se pueden romper.",
               f"{len(df):,} planetas"),
        _etapa("modelo", "Modelo", "Gradient boosting entrenado con el criterio de los expertos.",
               f"{len(pred):,} planetas nuevos evaluados"),
        _etapa("app", "Esta app", "Lee solo lo público, con su propia identidad.",
               f"{int(df.en_disputa.sum())} planetas en disputa a la vista"),
    ]) + "</div>")

    st.space("medium")
    st.html('<div class="bloques">' + "".join([
        _bloque("gobernanza", "Gobernanza con Unity Catalog",
                "La app corre con su propio service principal y solo puede leer el catálogo público. Un row filter "
                "esconde los planetas que la NASA tiene en disputa, y las etiquetas dicen qué guarda cada tabla."),
        _bloque("calidad", "Calidad",
                "Gold tiene reglas que no se pueden romper: el ESI va de 0 a 1 y el radio es positivo (constraints "
                "CHECK). Si llega un dato malo, la escritura falla en vez de ensuciar la tabla."),
        _bloque("orquestacion", "Orquestación",
                "Un job corre solo cuando llega un lote nuevo de la NASA (trigger por llegada de archivo): bronze, "
                "silver, gold y modelo. Una alerta avisa cada mañana si aparece un candidato con ESI de 0.9 o más."),
    ]) + "</div>")

    st.space("medium")
    c.seccion("El parecido a la Tierra (ESI)", "versión de dos variables del PHL @ UPR Arecibo")
    st.html('<div class="formula"><span class="mono">ESI = 1 − √( ½ · [ ((S − 1) / (S + 1))² + ((R − 1) / (R + 1))² ] )'
            '</span><p>S es la luz que recibe el planeta y R su radio, los dos comparados con la Tierra. Un ESI de 1 '
            'sería idéntico a la Tierra; mientras más bajo, menos se parece.</p></div>')
