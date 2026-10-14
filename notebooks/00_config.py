# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto final · 00 · Configuración
# MAGIC
# MAGIC Este notebook crea el catálogo, los esquemas y el volume donde aterrizan tus archivos.
# MAGIC
# MAGIC **Catálogo del proyecto:** `pf_ledezma`, el mismo nombre en los seis notebooks.
# MAGIC
# MAGIC La carpeta trae un **dataset de ejemplo** (las ventas de `samples.bakehouse`) para que corra completa desde el primer día. Tu entrega usa **tus propios datos**: cuando los tengas, súbelos al volume `landing` y cambia la ruta y el formato en `01_bronze`.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE CATALOG IF NOT EXISTS pf_ledezma;
# MAGIC CREATE SCHEMA IF NOT EXISTS pf_ledezma.bronze;
# MAGIC CREATE SCHEMA IF NOT EXISTS pf_ledezma.silver;
# MAGIC CREATE SCHEMA IF NOT EXISTS pf_ledezma.gold;
# MAGIC CREATE VOLUME IF NOT EXISTS pf_ledezma.bronze.landing;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Datos de ejemplo, en lotes
# MAGIC
# MAGIC Cada corrida de esta celda escribe **un lote** de archivos JSON en `landing/ventas/lote_N`. Sirve para probar que tu ingesta es incremental: corre `01_bronze`, cambia el lote a 2, vuelve a correr esta celda y después `01_bronze`. La segunda vez solo debe entrar el lote nuevo.
# MAGIC
# MAGIC Si ya trabajas con tus datos, no necesitas esta celda.

# COMMAND ----------

dbutils.widgets.dropdown("lote", "1", ["1", "2", "3"], "Lote de ejemplo")
lote = int(dbutils.widgets.get("lote"))

destino = f"/Volumes/pf_ledezma/bronze/landing/ventas/lote_{lote}"
ventas = spark.table("samples.bakehouse.sales_transactions")
(ventas.where(f"pmod(transactionID, 3) = {lote - 1}")
       .write.mode("overwrite").json(destino))

display(dbutils.fs.ls("/Volumes/pf_ledezma/bronze/landing/ventas/"))
