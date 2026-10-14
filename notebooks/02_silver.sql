-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 02 · Silver
-- MAGIC
-- MAGIC **Columna vertebral, parte 2 · Sección 3 del examen.** La tabla silver es la versión limpia de bronze.
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Tipos correctos (fechas como fecha, montos como número).
-- MAGIC - Nulos tratados con una regla que puedas explicar.
-- MAGIC - Deduplicación por la llave del negocio.
-- MAGIC - Al menos un join que enriquezca la tabla.
-- MAGIC - Una celda de métricas antes y después.

-- COMMAND ----------

USE CATALOG pf_ledezma;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: hoy esta tabla solo copia bronze. Agrega los tipos, los nulos, la deduplicación y el join.
CREATE OR REPLACE TABLE silver.ventas AS
SELECT *
FROM bronze.ventas_raw;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Métricas antes y después
-- MAGIC Ajusta las columnas a tu dataset: la llave del negocio y las columnas donde importa que no haya nulos.

-- COMMAND ----------

SELECT 'bronze' AS capa, count(*) AS filas, count(DISTINCT transactionID) AS llaves_distintas
FROM bronze.ventas_raw
UNION ALL
SELECT 'silver', count(*), count(DISTINCT transactionID)
FROM silver.ventas;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Qué regla usaste para los nulos y los duplicados, y por qué esa y no otra?
-- MAGIC
-- MAGIC _Escribe aquí._
