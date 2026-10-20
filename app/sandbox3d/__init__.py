"""Vista 3D del simulador: un componente de Streamlit (v2) con Three.js.

El modelo viaja al navegador como sus árboles, así la probabilidad cambia al instante mientras se arrastra
un control. Three.js se sirve desde app/static/three (static serving de Streamlit), sin depender de un CDN.
"""
from pathlib import Path
from typing import Callable

import numpy as np
import streamlit as st

_CARPETA = Path(__file__).parent
_componente = st.components.v2.component(
    "sandbox_3d",
    html=(_CARPETA / "escena.html").read_text(encoding="utf-8"),
    css=(_CARPETA / "escena.css").read_text(encoding="utf-8"),
    js=(_CARPETA / "escena.js").read_text(encoding="utf-8"),
)
_exportados: dict[int, dict] = {}


def exportar_modelo(modelo) -> dict | None:
    """Los árboles del gradient boosting en listas simples: [variable, umbral, izquierda, derecha] o [valor] en las hojas.

    Usa atributos internos de scikit-learn (fijo en 1.5.2 en requirements.txt); la probabilidad que da el
    navegador se comparó contra predict_proba.
    """
    if modelo is None or not hasattr(modelo, "_predictors"):
        return None
    clave = id(modelo)
    if clave not in _exportados:
        arboles = []
        for (arbol,) in modelo._predictors:
            arboles.append([
                [float(n["value"])] if n["is_leaf"]
                else [int(n["feature_idx"]), float(n["num_threshold"]), int(n["left"]), int(n["right"])]
                for n in arbol.nodes
            ])
        _exportados[clave] = {
            "base": float(np.ravel(modelo._baseline_prediction)[0]),
            "variables": list(modelo.feature_names_in_),
            "arboles": arboles,
        }
    return _exportados[clave]


def mostrar(planeta: dict, version: int, modelo, al_cambiar: Callable[[], None]) -> None:
    """Dibuja la escena. `version` solo sube cuando Python cambia el planeta (presets, "Traer", la ficha)."""
    _componente(
        data={"planeta": planeta, "version": version, "modelo": exportar_modelo(modelo)},
        key="sim3d",
        on_planeta_change=al_cambiar,
        width="stretch",
    )
