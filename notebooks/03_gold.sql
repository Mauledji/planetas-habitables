-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 03 · Gold y calidad
-- MAGIC
-- MAGIC **Componente 1 · Sección 3 del examen.** Una tabla gold que responde una pregunta de negocio, con reglas de calidad que Databricks hace cumplir.
-- MAGIC
-- MAGIC **La pregunta:** ¿qué planetas confirmados se parecen más a la Tierra, incluidos los que el catálogo de expertos de la UPR todavía no evalúa?
-- MAGIC
-- MAGIC | Objeto | Para qué |
-- MAGIC |---|---|
-- MAGIC | `gold.ranking_habitabilidad` | El ranking. Lleva las reglas de calidad (`NOT NULL` y `CHECK`) |
-- MAGIC | `gold.catalogo_publico` | Lo que ve el público y la app. Es el ranking, pero sin reglas `CHECK` porque ahí va el row filter (ver `04_gobernanza`) |
-- MAGIC | `gold.historial_mediciones` | Vista con todas las mediciones de los planetas publicados, para la ficha de la app |
-- MAGIC | `gold.prediccion_habitabilidad` | Lo que dice el modelo de machine learning de los planetas sin evaluar (la llena `07_ml_predecir`) |
-- MAGIC | `gold.modelo_publicado` | Copia del modelo elegido para que la app lo use en el simulador |
-- MAGIC
-- MAGIC La prueba de la fila mala que se rechaza está en `03b_prueba_calidad`, para que el job no la corra.

-- COMMAND ----------

CREATE WIDGET TEXT catalogo DEFAULT 'pf_ledezma';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Cómo se calcula
-- MAGIC
-- MAGIC - **ESI** (índice de parecido a la Tierra, versión simplificada del Planetary Habitability Laboratory), con `S` = insolación y `R` = radio, ambos en unidades de la Tierra:
-- MAGIC   `ESI = 1 − √( ½ · [ ((S−1)/(S+1))² + ((R−1)/(R+1))² ] )`. La Tierra da 1.
-- MAGIC - **Zona habitable**, con los límites de Kopparapu et al. (2013) para una estrella como el Sol: conservadora entre 0.356 y 1.107 veces la luz que recibe la Tierra, optimista entre 0.32 y 1.776.
-- MAGIC - **Tamaño:** rocoso (< 1.6 radios terrestres), supertierra (1.6 a 2.5), minineptuno (2.5 a 6) o gigante.
-- MAGIC - **Potencialmente habitable:** conservador si está en la zona conservadora y mide entre 0.5 y 1.6 radios terrestres; optimista si está en la zona optimista y mide hasta 2.5.
-- MAGIC
-- MAGIC La tabla se crea una sola vez con sus reglas y el job la refresca con `INSERT OVERWRITE`, así las reglas no se pierden en cada corrida.

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS gold.ranking_habitabilidad (
  planeta                  STRING  NOT NULL COMMENT 'Nombre oficial del planeta',
  estrella                 STRING  COMMENT 'Estrella que orbita',
  tipo_espectral           STRING,
  temp_estrella_k          DOUBLE,
  distancia_anios_luz      DOUBLE  COMMENT 'Distancia desde la Tierra',
  radio_tierras            DOUBLE  NOT NULL,
  fuente_radio             STRING  COMMENT 'medición oficial, otra publicación o estimado con la masa',
  masa_tierras             DOUBLE,
  insolacion_tierras       DOUBLE  NOT NULL COMMENT 'Luz que recibe comparada con la Tierra',
  fuente_insolacion        STRING  COMMENT 'medición oficial, otra publicación o calculada con la luminosidad',
  temp_equilibrio_k        DOUBLE,
  periodo_dias             DOUBLE,
  esi                      DOUBLE  NOT NULL COMMENT 'Índice de parecido a la Tierra calculado por este pipeline (0 a 1)',
  tamano                   STRING,
  zona_habitable           STRING  COMMENT 'conservadora, optimista o fuera',
  potencialmente_habitable STRING  COMMENT 'conservador, optimista o no',
  esi_expertos             DOUBLE  COMMENT 'ESI del Habitable Worlds Catalog (UPR)',
  habitable_expertos       STRING,
  evaluado_por_expertos    BOOLEAN COMMENT 'Falso si el catálogo de la UPR todavía no lo tiene',
  anio_descubrimiento      INT,
  metodo_descubrimiento    STRING,
  instalacion              STRING,
  en_disputa               BOOLEAN NOT NULL COMMENT 'La NASA marca su existencia como discutida',
  ra                       DOUBLE,
  dec                      DOUBLE,
  referencia               STRING,
  link_referencia          STRING,
  mediciones               BIGINT  COMMENT 'Cuántas publicaciones lo midieron',
  actualizado              TIMESTAMP
)
COMMENT 'Pregunta de negocio: qué planetas confirmados se parecen más a la Tierra, incluidos los que el catálogo de expertos todavía no evalúa';

-- COMMAND ----------

-- Reglas de calidad (además de los NOT NULL de la tabla)
ALTER TABLE gold.ranking_habitabilidad DROP CONSTRAINT IF EXISTS esi_valido;
ALTER TABLE gold.ranking_habitabilidad ADD CONSTRAINT esi_valido CHECK (esi BETWEEN 0 AND 1);
ALTER TABLE gold.ranking_habitabilidad DROP CONSTRAINT IF EXISTS radio_positivo;
ALTER TABLE gold.ranking_habitabilidad ADD CONSTRAINT radio_positivo CHECK (radio_tierras > 0);

-- COMMAND ----------

INSERT OVERWRITE gold.ranking_habitabilidad BY NAME
SELECT
  planeta, estrella, tipo_espectral, temp_estrella_k, distancia_anios_luz,
  radio_tierras, fuente_radio, masa_tierras, insolacion_tierras, fuente_insolacion,
  temp_equilibrio_k, periodo_dias,
  round(esi, 4) AS esi,
  CASE WHEN radio_tierras < 1.6 THEN 'rocoso'
       WHEN radio_tierras < 2.5 THEN 'supertierra'
       WHEN radio_tierras < 6   THEN 'minineptuno'
       ELSE 'gigante' END AS tamano,
  CASE WHEN insolacion_tierras BETWEEN 0.356 AND 1.107 THEN 'conservadora'
       WHEN insolacion_tierras BETWEEN 0.32 AND 1.776  THEN 'optimista'
       ELSE 'fuera' END AS zona_habitable,
  CASE WHEN insolacion_tierras BETWEEN 0.356 AND 1.107 AND radio_tierras BETWEEN 0.5 AND 1.6 THEN 'conservador'
       WHEN insolacion_tierras BETWEEN 0.32 AND 1.776 AND radio_tierras <= 2.5 THEN 'optimista'
       ELSE 'no' END AS potencialmente_habitable,
  esi_expertos, habitable_expertos, evaluado_por_expertos,
  anio_descubrimiento, metodo_descubrimiento, instalacion, en_disputa,
  ra, dec, referencia, link_referencia, mediciones,
  current_timestamp() AS actualizado
FROM (
  SELECT *,
         1 - sqrt(0.5 * (power((insolacion_tierras - 1) / (insolacion_tierras + 1), 2)
                       + power((radio_tierras - 1) / (radio_tierras + 1), 2))) AS esi
  FROM silver.planetas
  WHERE datos_suficientes AND radio_tierras > 0
);

-- COMMAND ----------

-- Las restricciones CHECK aparecen como propiedades delta.constraints.<nombre>
SHOW TBLPROPERTIES gold.ranking_habitabilidad;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Tabla pública y vista del historial

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS gold.catalogo_publico
COMMENT 'Lo que ve el público y la app: el ranking de habitabilidad, con row filter para los planetas en disputa'
AS SELECT * FROM gold.ranking_habitabilidad LIMIT 0;

INSERT OVERWRITE gold.catalogo_publico SELECT * FROM gold.ranking_habitabilidad;

-- IF NOT EXISTS y no OR REPLACE: reemplazar la vista borra los permisos que le da 04_gobernanza
CREATE VIEW IF NOT EXISTS gold.historial_mediciones
COMMENT 'Todas las mediciones de los planetas publicados, para la ficha de la app'
AS
SELECT m.planeta, m.referencia, m.link_referencia, m.fecha_publicacion, m.es_oficial,
       m.radio_tierras, m.masa_tierras, m.insolacion_tierras, m.temp_equilibrio_k, m.periodo_dias
FROM silver.mediciones m
WHERE m.planeta IN (SELECT planeta FROM gold.catalogo_publico);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Tabla para las predicciones del modelo
-- MAGIC La llena `07_ml_predecir` (extra de machine learning). La defino aquí para que todas las tablas gold vivan en el mismo notebook.

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS gold.prediccion_habitabilidad (
  planeta                 STRING    NOT NULL COMMENT 'Planeta que el catálogo de expertos todavía no evalúa',
  probabilidad            DOUBLE    NOT NULL COMMENT 'Qué tan seguro está el modelo de que es habitable (0 a 1)',
  habitable_segun_modelo  BOOLEAN   NOT NULL,
  habitable_segun_regla   BOOLEAN   COMMENT 'Lo que dice mi regla de zona habitable y tamaño',
  esi                     DOUBLE,
  modelo_run_id           STRING    NOT NULL COMMENT 'Corrida de MLflow del modelo que hizo la predicción',
  predicho_en             TIMESTAMP NOT NULL
)
COMMENT 'Predicciones del modelo de machine learning para los planetas que el catálogo de expertos todavía no evalúa';

ALTER TABLE gold.prediccion_habitabilidad DROP CONSTRAINT IF EXISTS probabilidad_valida;
ALTER TABLE gold.prediccion_habitabilidad ADD CONSTRAINT probabilidad_valida CHECK (probabilidad BETWEEN 0 AND 1);

-- Copia del modelo para la app: en Free Edition la red de las apps no llega al almacenamiento donde MLflow
-- guarda los artefactos, así que el job publica aquí el modelo elegido y la app lo lee por SQL
CREATE TABLE IF NOT EXISTS gold.modelo_publicado (
  modelo_run_id STRING    NOT NULL COMMENT 'Corrida de MLflow de donde sale el modelo',
  modelo        BINARY    NOT NULL COMMENT 'El modelo serializado con pickle (scikit-learn 1.5.2)',
  variables     STRING    NOT NULL COMMENT 'Las variables que pide el modelo',
  publicado_en  TIMESTAMP NOT NULL
)
COMMENT 'Copia del modelo elegido para que la app lo use (solo lo escribe 07_ml_predecir)';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### La respuesta: los planetas más parecidos a la Tierra

-- COMMAND ----------

SELECT planeta, estrella, round(distancia_anios_luz) AS anios_luz, round(radio_tierras, 2) AS radio,
       round(insolacion_tierras, 2) AS insolacion, esi, potencialmente_habitable,
       esi_expertos, evaluado_por_expertos
FROM gold.ranking_habitabilidad
WHERE potencialmente_habitable <> 'no' AND NOT en_disputa
ORDER BY esi DESC
LIMIT 15;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Los nuevos: candidatos que el catálogo de expertos todavía no evalúa

-- COMMAND ----------

SELECT planeta, estrella, anio_descubrimiento, round(distancia_anios_luz) AS anios_luz,
       round(radio_tierras, 2) AS radio, fuente_radio, round(insolacion_tierras, 2) AS insolacion,
       esi, potencialmente_habitable
FROM gold.ranking_habitabilidad
WHERE NOT evaluado_por_expertos AND potencialmente_habitable <> 'no'
ORDER BY esi DESC
LIMIT 15;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### ¿Coincido con los expertos?
-- MAGIC Para los planetas que sí están en el catálogo de la UPR, comparo mi resultado con el de ellos.

-- COMMAND ----------

SELECT
  count(*)                                                                         AS planetas_comparados,
  round(corr(esi, esi_expertos), 3)                                                AS correlacion_esi,
  count_if(habitable_expertos <> 'no')                                             AS habitables_segun_expertos,
  count_if(potencialmente_habitable <> 'no')                                       AS habitables_segun_yo,
  count_if(habitable_expertos <> 'no' AND potencialmente_habitable <> 'no')        AS en_ambos,
  round(100 * avg(CASE WHEN (habitable_expertos <> 'no') = (potencialmente_habitable <> 'no')
                       THEN 1 ELSE 0 END), 1)                                      AS coincidencia_pct
FROM gold.ranking_habitabilidad
WHERE evaluado_por_expertos;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Qué pregunta de negocio responde tu tabla gold? ¿Por qué elegiste tabla, view o materialized view?
-- MAGIC
-- MAGIC Responde qué planetas confirmados se parecen más a la Tierra, contando también los que el catálogo de expertos de la UPR todavía no evalúa. El primero es Teegarden's Star b, con ESI 0.969, y entre los nuevos aparece GJ 3378 b, descubierto en 2026, que el catálogo de la UPR no tiene. Para saber si mi cálculo tiene sentido lo comparé con el de los expertos: coincido en el 99.5% de los planetas que ellos sí evaluaron.
-- MAGIC
-- MAGIC Elegí tabla porque las reglas de calidad (`NOT NULL` y `CHECK`) solo se pueden poner en una tabla Delta, no en una view, y una materialized view no se puede crear desde un notebook en serverless. La tabla se crea una vez con sus reglas y el job la refresca con `INSERT OVERWRITE`, para que las reglas no se pierdan en cada corrida.
