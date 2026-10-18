"""Acceso a las tablas gold y al modelo, con la identidad de la app (su service principal)."""
import os
import re

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

CATALOGO = os.getenv("CATALOGO", "pf_ledezma")
if not re.fullmatch(r"[a-z0-9_]+", CATALOGO):
    raise ValueError(f"Nombre de catálogo inválido: {CATALOGO}")

_config = Config()


def consultar(query: str, parametros: dict | None = None) -> pd.DataFrame:
    with sql.connect(
        server_hostname=_config.host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: _config.authenticate,
    ) as conexion, conexion.cursor() as cursor:
        cursor.execute(query, parametros or {})
        return cursor.fetchall_arrow().to_pandas()


@st.cache_data(ttl=600, show_spinner="Consultando el catálogo de planetas...")
def catalogo() -> pd.DataFrame:
    """Todos los planetas publicados (el row filter de Unity Catalog ya esconde los que están en disputa)."""
    return consultar(f"SELECT * FROM {CATALOGO}.gold.catalogo_publico")


@st.cache_data(ttl=600, show_spinner=False)
def predicciones() -> pd.DataFrame:
    """Lo que dice el modelo de los planetas que el catálogo de expertos todavía no evalúa."""
    return consultar(f"""SELECT planeta, probabilidad, habitable_segun_modelo, modelo_run_id, predicho_en
                         FROM {CATALOGO}.gold.prediccion_habitabilidad""")


@st.cache_data(ttl=600, show_spinner=False)
def historial(planeta: str) -> pd.DataFrame:
    return consultar(
        f"""SELECT fecha_publicacion, referencia, link_referencia, es_oficial,
                   radio_tierras, masa_tierras, insolacion_tierras, temp_equilibrio_k, periodo_dias
            FROM {CATALOGO}.gold.historial_mediciones
            WHERE planeta = :planeta
            ORDER BY fecha_publicacion DESC""",
        {"planeta": planeta},
    )


@st.cache_resource(show_spinner="Cargando el modelo...")
def cargar_modelo(run_id: str):
    """El mismo modelo que usa el job, cargado desde su corrida en MLflow (la app tiene permiso de lectura)."""
    import mlflow

    mlflow.set_tracking_uri("databricks")
    return mlflow.sklearn.load_model(f"runs:/{run_id}/modelo")


def modelo_actual(prediccion: pd.DataFrame):
    """El modelo con el que se hicieron las predicciones más recientes, o None si todavía no hay."""
    if prediccion.empty:
        return None
    run_id = prediccion.sort_values("predicho_en").modelo_run_id.iloc[-1]
    return cargar_modelo(run_id)
