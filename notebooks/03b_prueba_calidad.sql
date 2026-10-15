-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 03b · Prueba de calidad
-- MAGIC
-- MAGIC **Evidencia del componente 1.** Intento meter a gold un planeta que rompe una regla de calidad y Databricks lo rechaza.
-- MAGIC
-- MAGIC Este notebook **no** va en el job: su última celda falla a propósito y ese error es la evidencia.
-- MAGIC
-- MAGIC Las reglas de `gold.ranking_habitabilidad`:
-- MAGIC
-- MAGIC | Regla | Tipo | Qué exige |
-- MAGIC |---|---|---|
-- MAGIC | `planeta`, `radio_tierras`, `insolacion_tierras`, `esi`, `en_disputa` | `NOT NULL` | Que el dato venga |
-- MAGIC | `esi_valido` | `CHECK` | `esi BETWEEN 0 AND 1` |
-- MAGIC | `radio_positivo` | `CHECK` | `radio_tierras > 0` |

-- COMMAND ----------

CREATE WIDGET TEXT catalogo DEFAULT 'pf_ledezma';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

-- Las reglas CHECK que tiene la tabla
SHOW TBLPROPERTIES gold.ranking_habitabilidad ('delta.constraints.esi_valido');

-- COMMAND ----------

SHOW TBLPROPERTIES gold.ranking_habitabilidad ('delta.constraints.radio_positivo');

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### La fila mala
-- MAGIC Un planeta inventado con ESI 1.5. El ESI va de 0 a 1, así que la regla `esi_valido` lo tiene que rechazar.

-- COMMAND ----------

INSERT INTO gold.ranking_habitabilidad (planeta, radio_tierras, insolacion_tierras, esi, en_disputa)
VALUES ('Planeta inventado b', 1.0, 1.0, 1.5, false);
