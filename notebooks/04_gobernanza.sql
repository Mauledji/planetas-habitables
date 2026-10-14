-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 04 · Gobernanza
-- MAGIC
-- MAGIC **Componente 3 · Sección 7 del examen.**
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Privilegios con mínimo privilegio para un perfil de lectura (`account users` o tu segunda identidad), verificados con `SHOW GRANTS`.
-- MAGIC - Un row filter o un column mask controlado por una tabla de mapeo, como en el Laboratorio 4, con la evidencia de lo que ve tu usuario antes y después de cambiar el mapeo.
-- MAGIC - Tags en las columnas sensibles.

-- COMMAND ----------

USE CATALOG pf_ledezma;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: los GRANT del perfil de lectura. Recuerda que leer exige USE CATALOG, USE SCHEMA y SELECT.

-- COMMAND ----------

SHOW GRANTS ON CATALOG pf_ledezma;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: la tabla de mapeo, la función y el ALTER TABLE ... SET ROW FILTER o SET MASK.

-- COMMAND ----------

-- TU CÓDIGO ACÁ: los tags de las columnas sensibles (SET TAGS) y la consulta a information_schema.column_tags.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Quién ve qué en tu proyecto? Explícalo en tres líneas, como se lo explicarías a un auditor.
-- MAGIC
-- MAGIC _Escribe aquí._
