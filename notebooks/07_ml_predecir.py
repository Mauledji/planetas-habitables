# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 07 · Predecir con el modelo (extra)
# MAGIC
# MAGIC Es la cuarta tarea del job: después de gold, usa el modelo elegido en `06_ml_entrenar` para evaluar los planetas que el catálogo de expertos todavía no tiene. Cuando llega un lote nuevo de la NASA, los planetas nuevos se evalúan solos, sin reentrenar.
# MAGIC
# MAGIC El modelo se carga desde el experimento de MLflow con `runs:/<run_id>/modelo` (en Free Edition no se puede registrar en Unity Catalog). Cada predicción guarda qué corrida del modelo la hizo.

# COMMAND ----------

# MAGIC %md
# MAGIC La misma versión de scikit-learn con la que se entrenó el modelo (ver `06_ml_entrenar`).

# COMMAND ----------

# MAGIC %pip install -q scikit-learn==1.5.2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import re

import mlflow
import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, DoubleType, StringType, StructField, StructType

dbutils.widgets.text("catalogo", "pf_ledezma", "Catálogo")
catalogo = dbutils.widgets.get("catalogo")
assert re.fullmatch(r"[a-z0-9_]+", catalogo), f"Nombre de catálogo inválido: {catalogo}"

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks")
usuario = spark.sql("SELECT current_user()").first()[0]
experimento = f"/Users/{usuario}/planetas-habitables-ml-{catalogo}"

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1. El modelo elegido

# COMMAND ----------

corridas = mlflow.search_runs(experiment_names=[experimento], filter_string="tags.elegido = 'si'",
                              order_by=["start_time DESC"], max_results=1)
if corridas.empty:
    print(f"Todavía no hay un modelo elegido en {experimento}. Corre 06_ml_entrenar primero.")
    dbutils.notebook.exit("sin modelo")

run_id = corridas.iloc[0].run_id
modelo = mlflow.sklearn.load_model(f"runs:/{run_id}/modelo")
variables = list(modelo.feature_names_in_)
print(f"Modelo: {corridas.iloc[0]['params.modelo']} · corrida {run_id}")
print(f"Variables: {', '.join(variables)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2. Los planetas a evaluar
# MAGIC Los que el catálogo de expertos no tiene, con datos suficientes y sin los que están en disputa.

# COMMAND ----------

pendientes = spark.sql(f"""
  SELECT p.planeta, r.esi, r.potencialmente_habitable <> 'no' AS habitable_segun_regla,
         {', '.join(f'p.{v}' for v in variables)}
  FROM {catalogo}.silver.planetas p
  JOIN {catalogo}.gold.ranking_habitabilidad r USING (planeta)
  WHERE NOT p.evaluado_por_expertos AND p.datos_suficientes AND NOT p.en_disputa
""").toPandas()

if pendientes.empty:
    print("No hay planetas pendientes de evaluar.")
    dbutils.notebook.exit("sin planetas pendientes")

probabilidad = modelo.predict_proba(pendientes[variables])[:, 1]
predicciones = pd.DataFrame({
    "planeta": pendientes.planeta,
    "probabilidad": probabilidad.round(4),
    "habitable_segun_modelo": probabilidad >= 0.5,
    "habitable_segun_regla": pendientes.habitable_segun_regla.astype(bool),
    "esi": pendientes.esi,
    "modelo_run_id": run_id,
})
esquema = StructType([
    StructField("planeta", StringType(), False),
    StructField("probabilidad", DoubleType(), False),
    StructField("habitable_segun_modelo", BooleanType(), False),
    StructField("habitable_segun_regla", BooleanType(), True),
    StructField("esi", DoubleType(), True),
    StructField("modelo_run_id", StringType(), False),
])
(spark.createDataFrame(predicciones, schema=esquema)
      .withColumn("predicho_en", F.current_timestamp())
      .createOrReplaceTempView("predicciones_nuevas"))

# La tabla y su regla de calidad (probabilidad entre 0 y 1) se crean en 03_gold
spark.sql(f"INSERT OVERWRITE {catalogo}.gold.prediccion_habitabilidad BY NAME SELECT * FROM predicciones_nuevas")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3. Resultado

# COMMAND ----------

display(spark.sql(f"""
  SELECT count(*) AS planetas_evaluados,
         count_if(habitable_segun_modelo) AS habitables_segun_modelo,
         count_if(habitable_segun_regla) AS habitables_segun_mi_regla,
         count_if(habitable_segun_modelo AND habitable_segun_regla) AS en_los_dos
  FROM {catalogo}.gold.prediccion_habitabilidad
"""))

# COMMAND ----------

display(spark.sql(f"""
  SELECT planeta, round(probabilidad, 3) AS probabilidad, habitable_segun_modelo, habitable_segun_regla, esi
  FROM {catalogo}.gold.prediccion_habitabilidad
  ORDER BY probabilidad DESC, esi DESC
  LIMIT 15
"""))
