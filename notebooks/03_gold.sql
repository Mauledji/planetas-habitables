-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 03 · Gold y calidad
-- MAGIC
-- MAGIC **Componente 1 · Sección 3 del examen.** Una tabla o view gold que responda una pregunta de negocio, y reglas de calidad que se cumplan.
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Al menos un objeto gold con una pregunta de negocio clara.
-- MAGIC - Al menos **dos** reglas de calidad que Databricks haga cumplir: `NOT NULL`, `CHECK`, o expectations si usas pipelines declarativos.
-- MAGIC - La evidencia de que una fila mala **se rechaza**: el error literal en la salida de una celda.
-- MAGIC
-- MAGIC Recuerda: una materialized view no se crea desde un notebook en serverless. Si quieres una, créala en el editor SQL y deja aquí la consulta que la lee.

-- COMMAND ----------

USE CATALOG pf_ledezma;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: cambia este ejemplo por la pregunta de negocio de tu proyecto.
CREATE OR REPLACE TABLE gold.ventas_por_franquicia AS
SELECT franchiseID, count(*) AS transacciones, sum(totalPrice) AS venta_total
FROM silver.ventas
GROUP BY franchiseID;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: tus reglas de calidad. Este ejemplo exige que la venta total no sea negativa.
ALTER TABLE gold.ventas_por_franquicia DROP CONSTRAINT IF EXISTS venta_no_negativa;
ALTER TABLE gold.ventas_por_franquicia ADD CONSTRAINT venta_no_negativa CHECK (venta_total >= 0);

-- COMMAND ----------

-- Las restricciones CHECK aparecen como propiedades delta.constraints.<nombre>.
-- information_schema.table_constraints solo lista PRIMARY KEY y FOREIGN KEY.
SHOW TBLPROPERTIES gold.ventas_por_franquicia;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Evidencia: una fila que se rechaza
-- MAGIC Escribe un `INSERT` con una fila que rompa tu regla y córrelo a mano. **La celda tiene que fallar**: ese error es la evidencia. Déjala fallada en la entrega, y no la incluyas en el job.

-- COMMAND ----------

-- TU CÓDIGO ACÁ

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Qué pregunta de negocio responde tu tabla gold? ¿Por qué elegiste tabla, view o materialized view?
-- MAGIC
-- MAGIC _Escribe aquí._
