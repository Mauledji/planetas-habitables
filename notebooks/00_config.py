# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 00 · Configuración
# MAGIC
# MAGIC Este notebook crea el catálogo del proyecto, un esquema por capa y el volume donde aterrizan los archivos de la NASA.
# MAGIC
# MAGIC El mismo código sirve para los dos ambientes y se escoge con el parámetro **catalogo**:
# MAGIC - `pf_ledezma` → prod
# MAGIC - `pf_ledezma_dev` → dev, donde pruebo los cambios antes de pasarlos a prod

# COMMAND ----------

import re

dbutils.widgets.text("catalogo", "pf_ledezma", "Catálogo")
catalogo = dbutils.widgets.get("catalogo")
assert re.fullmatch(r"[a-z0-9_]+", catalogo), f"Nombre de catálogo inválido: {catalogo}"

# COMMAND ----------

esquemas = {
    "bronze": "Datos crudos tal como llegan de la NASA y la UPR",
    "silver": "Planetas limpios, deduplicados y enriquecidos",
    "gold": "Ranking de habitabilidad y catálogo público para la app",
    "gobernanza": "Tablas de mapeo y funciones de seguridad",
}

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalogo} COMMENT 'Proyecto final M4: buscador de planetas habitables'")
for esquema, comentario in esquemas.items():
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalogo}.{esquema} COMMENT '{comentario}'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalogo}.bronze.landing COMMENT 'Archivos que llegan por lotes'")

display(spark.sql(f"SHOW SCHEMAS IN {catalogo}"))
