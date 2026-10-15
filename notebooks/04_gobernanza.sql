-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 04 · Gobernanza
-- MAGIC
-- MAGIC **Componente 3 · Sección 7 del examen.**
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Catálogo con esquemas por capa.
-- MAGIC - Privilegios con mínimo privilegio para un perfil de lectura (`account users`), verificados con `SHOW GRANTS`.
-- MAGIC - Un row filter controlado por una tabla de mapeo, con la evidencia de lo que ve mi usuario antes y después de cambiar el mapeo.
-- MAGIC - Tags en las columnas sensibles.
-- MAGIC
-- MAGIC | Perfil | Qué puede leer | ¿Ve los planetas en disputa? |
-- MAGIC |---|---|---|
-- MAGIC | Yo, con nivel `investigador` en la tabla de mapeo | Todo el catálogo | Sí |
-- MAGIC | Perfil de lectura: `account users` (cualquier usuario del workspace y la app) | Solo `gold.catalogo_publico` y `gold.historial_mediciones` | No |

-- COMMAND ----------

CREATE WIDGET TEXT catalogo DEFAULT 'pf_ledezma';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 1. Esquemas por capa

-- COMMAND ----------

SELECT schema_name AS esquema, comment AS para_que
FROM information_schema.schemata
WHERE schema_name IN ('bronze', 'silver', 'gold', 'gobernanza')
ORDER BY CASE schema_name WHEN 'bronze' THEN 1 WHEN 'silver' THEN 2 WHEN 'gold' THEN 3 ELSE 4 END;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 2. Perfil de lectura con mínimo privilegio
-- MAGIC Para leer una tabla hacen falta tres permisos: `USE CATALOG`, `USE SCHEMA` y `SELECT`. Al perfil de lectura le doy solo lo publicado en gold. No recibe nada en bronze, silver ni en el ranking interno.

-- COMMAND ----------

GRANT USE CATALOG ON CATALOG IDENTIFIER(:catalogo) TO `account users`;
GRANT USE SCHEMA ON SCHEMA gold TO `account users`;
GRANT SELECT ON TABLE gold.catalogo_publico TO `account users`;
GRANT SELECT ON TABLE gold.historial_mediciones TO `account users`;

-- COMMAND ----------

SHOW GRANTS `account users` ON CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

SHOW GRANTS `account users` ON SCHEMA gold;

-- COMMAND ----------

SHOW GRANTS ON TABLE gold.catalogo_publico;

-- COMMAND ----------

-- En silver no tiene ningún permiso: este resultado sale vacío
SHOW GRANTS `account users` ON SCHEMA silver;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 3. Row filter controlado por una tabla de mapeo
-- MAGIC
-- MAGIC La NASA marca algunos planetas como "en disputa" porque su existencia todavía se discute. En el catálogo público solo los ve quien tenga nivel `investigador` en `gobernanza.mapa_acceso`. Quien no aparece en la tabla es público.
-- MAGIC
-- MAGIC El filtro va en `gold.catalogo_publico` y no en el ranking porque Unity Catalog no deja poner un row filter en una tabla con reglas `CHECK` (lo probé y da `ROW_LEVEL_SECURITY_FEATURE_NOT_SUPPORTED.CHECK_CONSTRAINT`).

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS gobernanza.mapa_acceso (
  correo STRING NOT NULL COMMENT 'Correo de la persona',
  nivel  STRING NOT NULL COMMENT 'publico o investigador'
)
COMMENT 'Tabla de mapeo: qué nivel de acceso tiene cada persona. Quien no aparece es público.';

MERGE INTO gobernanza.mapa_acceso m
USING (SELECT current_user() AS correo, 'investigador' AS nivel) n
ON m.correo = n.correo
WHEN MATCHED THEN UPDATE SET m.nivel = n.nivel
WHEN NOT MATCHED THEN INSERT (correo, nivel) VALUES (n.correo, n.nivel);

-- COMMAND ----------

CREATE OR REPLACE FUNCTION gobernanza.puede_ver_planeta(en_disputa BOOLEAN)
RETURNS BOOLEAN
COMMENT 'Los planetas en disputa solo los ve quien tenga nivel investigador en gobernanza.mapa_acceso'
RETURN NOT en_disputa
    OR EXISTS (SELECT 1
               FROM gobernanza.mapa_acceso m
               WHERE m.correo = current_user() AND m.nivel = 'investigador');

ALTER TABLE gold.catalogo_publico SET ROW FILTER gobernanza.puede_ver_planeta ON (en_disputa);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC **Evidencia.** Lo que veo con mi nivel en `investigador`, después de cambiarlo a `publico` y después de devolverlo.

-- COMMAND ----------

SELECT (SELECT nivel FROM gobernanza.mapa_acceso WHERE correo = current_user()) AS mi_nivel,
       count(*)              AS planetas_que_veo,
       count_if(en_disputa)  AS en_disputa_que_veo
FROM gold.catalogo_publico;

-- COMMAND ----------

UPDATE gobernanza.mapa_acceso SET nivel = 'publico' WHERE correo = current_user();

SELECT (SELECT nivel FROM gobernanza.mapa_acceso WHERE correo = current_user()) AS mi_nivel,
       count(*)              AS planetas_que_veo,
       count_if(en_disputa)  AS en_disputa_que_veo
FROM gold.catalogo_publico;

-- COMMAND ----------

UPDATE gobernanza.mapa_acceso SET nivel = 'investigador' WHERE correo = current_user();

SELECT (SELECT nivel FROM gobernanza.mapa_acceso WHERE correo = current_user()) AS mi_nivel,
       count(*)              AS planetas_que_veo,
       count_if(en_disputa)  AS en_disputa_que_veo
FROM gold.catalogo_publico;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 4. Tags en las columnas sensibles

-- COMMAND ----------

ALTER TABLE gobernanza.mapa_acceso ALTER COLUMN correo SET TAGS ('pii' = 'correo');
ALTER TABLE gold.ranking_habitabilidad ALTER COLUMN en_disputa SET TAGS ('clasificacion' = 'restringido');
ALTER TABLE gold.catalogo_publico ALTER COLUMN en_disputa SET TAGS ('clasificacion' = 'restringido');

-- COMMAND ----------

SELECT schema_name AS esquema, table_name AS tabla, column_name AS columna, tag_name, tag_value
FROM information_schema.column_tags
ORDER BY esquema, tabla, columna;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Quién ve qué en tu proyecto? Explícalo en tres líneas, como se lo explicarías a un auditor.
-- MAGIC
-- MAGIC 1. Yo soy el dueño del catálogo y tengo nivel `investigador` en la tabla de mapeo, así que veo todo, incluidos los 32 planetas que la NASA tiene en disputa.
-- MAGIC 2. Cualquier otro usuario del workspace y la app (`account users`) solo puede leer `gold.catalogo_publico` y `gold.historial_mediciones`; no tiene ningún permiso en bronze, silver ni en el ranking interno, como se ve en los `SHOW GRANTS`.
-- MAGIC 3. En el catálogo público, el row filter le esconde los planetas en disputa a quien no sea investigador: cuando me cambié a `publico` pasé de ver 5,290 planetas a 5,258, y el correo de la tabla de mapeo está etiquetado como dato personal.
