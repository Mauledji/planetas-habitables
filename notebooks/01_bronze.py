# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 01 · Bronze
# MAGIC
# MAGIC **Columna vertebral, parte 1 · Sección 2 del examen.** Ingesta **incremental** desde el volume `landing` hacia una tabla Delta gobernada.
# MAGIC
# MAGIC Lo que se evalúa:
# MAGIC - La ingesta usa Auto Loader (o `COPY INTO`) y guarda el esquema en `schemaLocation`.
# MAGIC - Una segunda corrida **solo carga los archivos nuevos**. La evidencia es la celda de conteo por lote, corrida después de cargar dos lotes.
# MAGIC - Cada fila sabe de qué archivo vino.

# COMMAND ----------

# TU CÓDIGO ACÁ: cuando uses tus datos, cambia la ruta, el formato y el nombre de la tabla.
origen = "/Volumes/pf_ledezma/bronze/landing/ventas/"
formato = "json"
tabla_bronze = "pf_ledezma.bronze.ventas_raw"
checkpoint = "/Volumes/pf_ledezma/bronze/landing/_checkpoints/ventas_raw"

# COMMAND ----------

from pyspark.sql import functions as F

(spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", formato)
    .option("cloudFiles.schemaLocation", checkpoint)
    .option("cloudFiles.inferColumnTypes", "true")
    .option("pathGlobFilter", f"*.{formato}")
    .load(origen)
    .withColumn("archivo_origen", F.col("_metadata.file_path"))
    .withColumn("fecha_ingesta", F.current_timestamp())
    .writeStream
    .option("checkpointLocation", checkpoint)
    .trigger(availableNow=True)   # en serverless es el único trigger que corre
    .toTable(tabla_bronze)
    .awaitTermination())

# COMMAND ----------

# MAGIC %md
# MAGIC ### Evidencia de la ingesta incremental
# MAGIC Corre esta celda después de cargar dos lotes. Cada lote debe aparecer **una sola vez**, con su propia hora de ingesta.

# COMMAND ----------

display(spark.sql(f"""
  SELECT regexp_extract(archivo_origen, 'lote_[0-9]+', 0) AS lote,
         count(*) AS filas,
         min(fecha_ingesta) AS ingestado
  FROM {tabla_bronze}
  GROUP BY 1 ORDER BY 1
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### TU RESPUESTA
# MAGIC ¿Qué pasaría si corres esta ingesta dos veces seguidas sin archivos nuevos? ¿Qué guarda el checkpoint para que eso pase?
# MAGIC
# MAGIC _Escribe aquí._
