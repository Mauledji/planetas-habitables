"""La ficha de un planeta: al lado del mapa en Explorar y en un diálogo en Nuevos descubrimientos."""
from html import escape

import pandas as pd
import streamlit as st

import calculos
import componentes as c
import datos
import simulador

ANIOS_VOYAGER_POR_ANIO_LUZ = 17_600  # la Voyager 1 viaja a unos 17 km/s
METODOS = {
    "Transit": "tránsito", "Radial Velocity": "velocidad radial", "Imaging": "imagen directa",
    "Microlensing": "microlente gravitacional", "Astrometry": "astrometría",
    "Transit Timing Variations": "variaciones del tránsito", "Eclipse Timing Variations": "variaciones de eclipses",
    "Orbital Brightness Modulation": "cambios de brillo en su órbita", "Pulsar Timing": "tiempos de un púlsar",
    "Pulsation Timing Variations": "variaciones de pulsación", "Disk Kinematics": "movimiento del disco",
}
REGLA = {"conservador": ("Mi regla: sí (conservador)", "habitable"),
         "optimista": ("Mi regla: sí (optimista)", "habitable"), "no": ("Mi regla: no", "")}
EXPERTOS = {"conservador": "Expertos UPR: sí (conservador)", "optimista": "Expertos UPR: sí (optimista)",
            "no": "Expertos UPR: no"}


def _chips(p: pd.Series, pred: pd.DataFrame) -> str:
    texto, tono = REGLA.get(p.potencialmente_habitable, REGLA["no"])
    chips = [c.chip(texto, tono)]
    if p.evaluado_por_expertos:
        habitable = p.habitable_expertos in ("conservador", "optimista")
        chips.append(c.chip(EXPERTOS.get(p.habitable_expertos, EXPERTOS["no"]), "habitable" if habitable else ""))
    else:
        prediccion = pred[pred.planeta == p.planeta]
        if prediccion.empty:
            chips.append(c.chip("Sin evaluar por expertos"))
        else:
            chips.append(c.chip(f"Modelo: {c.porcentaje(prediccion.iloc[0].probabilidad)} habitable", "modelo"))
    return f'<div class="chips">{"".join(chips)}</div>'


def _datos(p: pd.Series) -> str:
    distancia = "sin dato" if pd.isna(p.distancia_anios_luz) else f"{p.distancia_anios_luz:,.0f}"
    estrella = "sin dato" if pd.isna(p.temp_estrella_k) else f"{p.temp_estrella_k:,.0f} K"
    return c.datos_grid([
        ("Parecido a la Tierra", f"{p.esi:.3f}"),
        ("Radio (Tierra = 1)", f"{p.radio_tierras:.2f}"),
        ("Luz (Tierra = 1)", f"{p.insolacion_tierras:.2f}"),
        ("Años luz", distancia),
        ("Su estrella", estrella),
        ("Descubierto", "sin dato" if pd.isna(p.anio_descubrimiento) else str(int(p.anio_descubrimiento))),
    ])


def _nota(p: pd.Series) -> str:
    partes = []
    if pd.notna(p.metodo_descubrimiento):
        desde = f" desde {p.instalacion}" if pd.notna(p.instalacion) else ""
        partes.append(f"Descubierto por {METODOS.get(p.metodo_descubrimiento, p.metodo_descubrimiento)}{desde}.")
    if pd.notna(p.distancia_anios_luz):
        partes.append(f"La Voyager 1 tardaría unos {p.distancia_anios_luz * ANIOS_VOYAGER_POR_ANIO_LUZ:,.0f} años "
                      f"en llegar.")
    partes.append(f"Radio: {p.fuente_radio}. Luz: {p.fuente_insolacion}.")
    return f'<p class="nota">{escape(" ".join(partes))}</p>'


def mostrar(df: pd.DataFrame, pred: pd.DataFrame, nombre: str | None, clave: str = "ficha") -> None:
    filas = df[df.planeta == nombre]
    with st.container(key=clave):
        if filas.empty:
            st.html('<p class="ceja">Ficha</p><p class="tenue">Haz click en un planeta del mapa o búscalo arriba '
                    'para ver su ficha.</p>')
            return
        p = filas.iloc[0]
        tipo = calculos.aspecto(p.radio_tierras, p.insolacion_tierras)
        st.html(
            f'<div class="ficha-cabeza">{c.esfera(tipo, 78)}<div><p class="ceja">{escape(str(p.estrella))}</p>'
            f'<h3>{escape(p.planeta)}</h3><p class="ficha-sub">{escape(calculos.ASPECTOS[tipo])} '
            f'<span class="tenue">· ilustración</span></p></div></div>'
            + _chips(p, pred) + _datos(p) + _nota(p)
        )
        st.button("Experimentar con este planeta", icon=":material/science:", type="primary",
                  key=f"{clave}_experimentar", on_click=simulador.cargar, args=(p.to_dict(),))
        with st.expander(f"Sus {int(p.mediciones)} mediciones publicadas", icon=":material/history_edu:"):
            st.dataframe(datos.historial(p.planeta), hide_index=True, width="stretch", column_config={
                "fecha_publicacion": st.column_config.DateColumn("Publicada"),
                "referencia": st.column_config.TextColumn("Referencia"),
                "link_referencia": st.column_config.LinkColumn("Artículo", display_text="abrir"),
                "es_oficial": st.column_config.CheckboxColumn("Oficial"),
                "radio_tierras": st.column_config.NumberColumn("Radio", format="%.2f"),
                "masa_tierras": st.column_config.NumberColumn("Masa", format="%.2f"),
                "insolacion_tierras": st.column_config.NumberColumn("Luz", format="%.2f"),
                "temp_equilibrio_k": st.column_config.NumberColumn("Temp. (K)", format="%.0f"),
                "periodo_dias": st.column_config.NumberColumn("Año (días)", format="%.1f"),
            })
