# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 01 · Bronze
# MAGIC
# MAGIC **Columna vertebral, parte 1 · Sección 2 del examen.** Ingesta **incremental** desde el volume `landing` hacia tablas Delta en `bronze`.
# MAGIC
# MAGIC Cargo dos fuentes, cada una con su propio Auto Loader:
# MAGIC
# MAGIC | Fuente | Carpeta en `landing` | Tabla |
# MAGIC |---|---|---|
# MAGIC | Mediciones de exoplanetas (NASA Exoplanet Archive) | `mediciones/lote_N/` | `bronze.mediciones_raw` |
# MAGIC | Catálogo de habitabilidad (PHL, Universidad de Puerto Rico) | `habitabilidad/lote_N/` | `bronze.habitabilidad_raw` |
# MAGIC
# MAGIC Lo que se evalúa:
# MAGIC - La ingesta usa Auto Loader y guarda el esquema en `schemaLocation`.
# MAGIC - Una segunda corrida **solo carga los archivos nuevos**. La evidencia es la celda de conteo por lote, corrida después de cargar dos lotes.
# MAGIC - Cada fila sabe de qué archivo vino (`archivo_origen`).

# COMMAND ----------

import re

from pyspark.sql import functions as F

dbutils.widgets.text("catalogo", "pf_ledezma", "Catálogo")
catalogo = dbutils.widgets.get("catalogo")
assert re.fullmatch(r"[a-z0-9_]+", catalogo), f"Nombre de catálogo inválido: {catalogo}"

landing = f"/Volumes/{catalogo}/bronze/landing"

# COMMAND ----------

def ingestar(fuente: str, tabla: str) -> None:
    """Carga a bronze solo los archivos de landing/<fuente>/ que todavía no se han procesado."""
    checkpoint = f"{landing}/_checkpoints/{tabla}"
    (spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.schemaLocation", checkpoint)
        .option("cloudFiles.inferColumnTypes", "true")
        .option("pathGlobFilter", "*.csv")
        .load(f"{landing}/{fuente}/")
        .withColumn("archivo_origen", F.col("_metadata.file_path"))
        .withColumn("fecha_ingesta", F.current_timestamp())
        .writeStream
        .option("checkpointLocation", checkpoint)
        .trigger(availableNow=True)   # en serverless es el único trigger que corre
        .toTable(f"{catalogo}.bronze.{tabla}")
        .awaitTermination())

# COMMAND ----------

ingestar("mediciones", "mediciones_raw")
ingestar("habitabilidad", "habitabilidad_raw")

spark.sql(f"COMMENT ON TABLE {catalogo}.bronze.mediciones_raw IS "
          "'Mediciones de exoplanetas tal como llegan de la NASA, una fila por publicación'")
spark.sql(f"COMMENT ON TABLE {catalogo}.bronze.habitabilidad_raw IS "
          "'Habitable Worlds Catalog (PHL @ UPR Arecibo) tal como llega'")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Evidencia de la ingesta incremental
# MAGIC Cada lote debe aparecer **una sola vez**, con su propia hora de ingesta.

# COMMAND ----------

display(spark.sql(f"""
  SELECT 'mediciones_raw' AS tabla,
         regexp_extract(archivo_origen, 'lote_[0-9]+', 0) AS lote,
         count(*) AS filas,
         count(DISTINCT pl_name) AS planetas,
         min(fecha_ingesta) AS ingestado
  FROM {catalogo}.bronze.mediciones_raw
  GROUP BY 1, 2
  UNION ALL
  SELECT 'habitabilidad_raw',
         regexp_extract(archivo_origen, 'lote_[0-9]+', 0),
         count(*),
         count(DISTINCT P_NAME),
         min(fecha_ingesta)
  FROM {catalogo}.bronze.habitabilidad_raw
  GROUP BY 1, 2
  ORDER BY 1, 2
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Prueba: la corro otra vez sin archivos nuevos

# COMMAND ----------

antes = spark.table(f"{catalogo}.bronze.mediciones_raw").count()
ingestar("mediciones", "mediciones_raw")
despues = spark.table(f"{catalogo}.bronze.mediciones_raw").count()
print(f"Antes: {antes:,} filas · Después de volver a correr: {despues:,} filas · Filas nuevas: {despues - antes}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### TU RESPUESTA
# MAGIC ¿Qué pasaría si corres esta ingesta dos veces seguidas sin archivos nuevos? ¿Qué guarda el checkpoint para que eso pase?
# MAGIC
# MAGIC No entra ninguna fila. En la celda de arriba la volví a correr y las filas nuevas salen en 0: Auto Loader revisa la carpeta, ve que todos los archivos ya los procesó y termina sin escribir nada.
# MAGIC
# MAGIC Eso funciona por el checkpoint. Ahí Auto Loader guarda la lista de archivos que ya leyó y hasta dónde llegó, y en `schemaLocation` guarda el esquema que infirió la primera vez, para no tener que adivinarlo en cada corrida. Si borrara el checkpoint, volvería a leer todos los archivos desde cero y las mediciones quedarían duplicadas en bronze.
