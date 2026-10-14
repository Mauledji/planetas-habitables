-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 05 · Observabilidad y optimización
-- MAGIC
-- MAGIC **Componente 5 · Secciones 6 y 7 del examen.**
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Una consulta a las tablas del sistema sobre **tu** proyecto: auditoría, linaje o corridas del job.
-- MAGIC - Liquid clustering en tu tabla más grande, con `OPTIMIZE` y la evidencia en `DESCRIBE DETAIL` o `DESCRIBE HISTORY`.
-- MAGIC
-- MAGIC Las tablas del sistema llegan con atraso: la auditoría, minutos; el linaje, unos 20. Si una consulta sale vacía, vuelve a correrla más tarde.

-- COMMAND ----------

-- Lo que se hizo sobre tu catálogo en los últimos 7 días
SELECT event_time, action_name,
       coalesce(request_params['full_name_arg'], request_params['name']) AS objeto
FROM system.access.audit
WHERE user_identity.email = current_user()
  AND event_date >= current_date() - INTERVAL 7 DAYS
  AND lower(to_json(request_params)) LIKE '%pf_ledezma%'
  AND action_name RLIKE '^(create|update|delete)'
ORDER BY event_time DESC
LIMIT 50;

-- COMMAND ----------

-- De dónde se alimenta cada tabla de tu proyecto
SELECT DISTINCT source_table_full_name, target_table_full_name, entity_type
FROM system.access.table_lineage
WHERE target_table_full_name LIKE 'pf_ledezma.%'
  AND event_date >= current_date() - INTERVAL 7 DAYS;

-- COMMAND ----------

-- TU CÓDIGO ACÁ: una consulta a system.lakeflow.job_run_timeline sobre las corridas de tu job.

-- COMMAND ----------

-- TU CÓDIGO ACÁ: cambia la tabla y la columna por las de tu proyecto.
ALTER TABLE pf_ledezma.silver.ventas CLUSTER BY (franchiseID);
OPTIMIZE pf_ledezma.silver.ventas;

-- COMMAND ----------

DESCRIBE DETAIL pf_ledezma.silver.ventas;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Por qué elegiste esa columna para el clustering? ¿Qué consulta de tu proyecto se beneficia?
-- MAGIC
-- MAGIC _Escribe aquí._
