-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 05 · Observabilidad y optimización
-- MAGIC
-- MAGIC **Componente 5 · Secciones 6 y 7 del examen.**
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Una consulta a las tablas del sistema sobre **mi** proyecto: auditoría, linaje y corridas del job.
-- MAGIC - Liquid clustering en mi tabla más grande, con `OPTIMIZE` y la evidencia en `DESCRIBE DETAIL` y `DESCRIBE HISTORY`.
-- MAGIC
-- MAGIC Las tablas del sistema llegan con atraso: la auditoría, minutos; el linaje, unos 20. Si una consulta sale vacía, hay que volver a correrla más tarde.

-- COMMAND ----------

CREATE WIDGET TEXT catalogo DEFAULT 'pf_ledezma';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 1. Auditoría: qué se hizo sobre mi catálogo en los últimos 7 días

-- COMMAND ----------

SELECT event_time, action_name,
       coalesce(request_params['full_name_arg'], request_params['name']) AS objeto
FROM system.access.audit
WHERE user_identity.email = current_user()
  AND event_date >= current_date() - INTERVAL 7 DAYS
  AND lower(to_json(request_params)) LIKE '%' || :catalogo || '.%'
  AND action_name RLIKE '^(create|update|delete)'
ORDER BY event_time DESC
LIMIT 50;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 2. Linaje: de dónde se alimenta cada tabla

-- COMMAND ----------

SELECT DISTINCT
       coalesce(source_table_full_name, source_path) AS origen,
       target_table_full_name                        AS destino,
       entity_type                                   AS hecho_desde
FROM system.access.table_lineage
WHERE target_table_full_name LIKE :catalogo || '.%'
  AND coalesce(source_table_full_name, source_path) IS NOT NULL
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY destino, origen;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 3. Corridas del job

-- COMMAND ----------

WITH jobs AS (
  SELECT job_id, name
  FROM system.lakeflow.jobs
  QUALIFY row_number() OVER (PARTITION BY job_id ORDER BY change_time DESC) = 1
)
SELECT j.name                                                            AS job,
       r.run_id,
       r.trigger_type                                                    AS disparador,
       max(r.result_state)                                               AS resultado,
       min(r.period_start_time)                                          AS inicio,
       round(timestampdiff(SECOND, min(r.period_start_time), max(r.period_end_time)) / 60.0, 1) AS minutos
FROM system.lakeflow.job_run_timeline r
JOIN jobs j USING (job_id)
WHERE j.name LIKE 'pf_ledezma pipeline%'
  AND r.period_start_time >= current_date() - INTERVAL 7 DAYS
GROUP BY ALL
ORDER BY inicio DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 4. Liquid clustering
-- MAGIC
-- MAGIC Mi tabla más grande es `bronze.mediciones_raw`: todas las mediciones tal como llegan de la NASA, y crece con cada lote. La agrupo por el nombre del planeta (`pl_name`). También agrupo `silver.mediciones` por `planeta`, porque es la que consulta la ficha de la app.

-- COMMAND ----------

-- La tabla más grande del proyecto
SELECT 'bronze.mediciones_raw' AS tabla, count(*) AS filas FROM bronze.mediciones_raw
UNION ALL SELECT 'silver.mediciones', count(*) FROM silver.mediciones
UNION ALL SELECT 'silver.planetas', count(*) FROM silver.planetas
ORDER BY filas DESC;

-- COMMAND ----------

ALTER TABLE bronze.mediciones_raw CLUSTER BY (pl_name);

-- COMMAND ----------

OPTIMIZE bronze.mediciones_raw;

-- COMMAND ----------

-- clusteringColumns muestra la columna por la que se agrupan los datos
DESCRIBE DETAIL bronze.mediciones_raw;

-- COMMAND ----------

DESCRIBE HISTORY bronze.mediciones_raw LIMIT 5;

-- COMMAND ----------

-- Lo mismo en silver, que es la que lee la app
ALTER TABLE silver.mediciones CLUSTER BY (planeta);
OPTIMIZE silver.mediciones;

-- COMMAND ----------

DESCRIBE DETAIL silver.mediciones;

-- COMMAND ----------

-- Las consultas que se benefician: revisar los datos crudos de un planeta (bronze)...
SELECT pl_name, regexp_extract(pl_refname, '>([^<]+)</a>', 1) AS publicacion, releasedate, archivo_origen
FROM bronze.mediciones_raw
WHERE pl_name = 'TRAPPIST-1 e'
ORDER BY releasedate;

-- COMMAND ----------

-- ...y la ficha de un planeta en la app (silver, a través de la vista de gold)
SELECT planeta, referencia, fecha_publicacion, es_oficial, radio_tierras, insolacion_tierras
FROM gold.historial_mediciones
WHERE planeta = 'TRAPPIST-1 e'
ORDER BY fecha_publicacion;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Por qué elegiste esa columna para el clustering? ¿Qué consulta de tu proyecto se beneficia?
-- MAGIC
-- MAGIC Elegí el nombre del planeta (`pl_name` en bronze, `planeta` en silver) porque es por donde se consulta: cuando quiero revisar los datos crudos de un planeta, por ejemplo de qué publicación salió un valor, filtro bronze por `pl_name`; y la ficha de la app pide todas las mediciones de un planeta (las consultas de arriba, con `TRAPPIST-1 e`). Con liquid clustering las filas de un mismo planeta quedan juntas y Databricks se puede saltar los archivos que no lo tienen.
-- MAGIC
-- MAGIC Hoy las tablas son pequeñas (unas 40 mil filas) y la diferencia casi no se nota, pero bronze crece con cada lote de la NASA. A diferencia de particionar, no tengo que escoger particiones fijas ni preocuparme por crear miles de particiones chiquitas, porque hay miles de planetas distintos.
