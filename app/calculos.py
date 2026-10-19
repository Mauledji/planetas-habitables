"""Los mismos cálculos que gold (ESI y mi regla), más las predicciones del modelo para el simulador."""
import numpy as np
import pandas as pd

ZONA_CONSERVADORA = (0.356, 1.107)  # Kopparapu et al. (2013), estrella como el Sol
ZONA_OPTIMISTA = (0.32, 1.776)

LUZ_MIN, LUZ_MAX = 0.05, 4.0
RADIO_MIN, RADIO_MAX = 0.3, 4.0


def esi(radio: float, luz: float) -> float:
    return 1 - np.sqrt(0.5 * (((luz - 1) / (luz + 1)) ** 2 + ((radio - 1) / (radio + 1)) ** 2))


def segun_regla(radio: float, luz: float) -> str:
    if ZONA_CONSERVADORA[0] <= luz <= ZONA_CONSERVADORA[1] and 0.5 <= radio <= 1.6:
        return "conservador"
    if ZONA_OPTIMISTA[0] <= luz <= ZONA_OPTIMISTA[1] and radio <= 2.5:
        return "optimista"
    return "no"


def _entrada(modelo, radio, luz, temp) -> pd.DataFrame:
    """Arma las variables que pide el modelo; las que no controla el simulador van vacías (el modelo acepta nulos)."""
    datos = pd.DataFrame({"radio_tierras": np.atleast_1d(radio), "insolacion_tierras": np.atleast_1d(luz),
                          "temp_estrella_k": np.atleast_1d(temp)})
    for variable in modelo.feature_names_in_:
        if variable not in datos:
            datos[variable] = np.nan
    return datos[list(modelo.feature_names_in_)]


def probabilidad(modelo, radio: float, luz: float, temp: float) -> float:
    return float(modelo.predict_proba(_entrada(modelo, radio, luz, temp))[0, 1])


def grilla(modelo, temp: float, puntos: int = 70) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Probabilidad del modelo en una grilla de luz x radio, para una estrella de cierta temperatura."""
    luz = np.logspace(np.log10(LUZ_MIN), np.log10(LUZ_MAX), puntos)
    radio = np.linspace(RADIO_MIN, RADIO_MAX, puntos)
    malla_luz, malla_radio = np.meshgrid(luz, radio)
    prob = modelo.predict_proba(_entrada(modelo, malla_radio.ravel(), malla_luz.ravel(),
                                         np.full(malla_luz.size, temp)))[:, 1]
    return luz, radio, prob.reshape(malla_luz.shape)
