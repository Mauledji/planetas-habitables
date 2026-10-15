-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Proyecto final · 02 · Silver
-- MAGIC
-- MAGIC **Columna vertebral, parte 2 · Sección 3 del examen.** Silver es la versión limpia de bronze.
-- MAGIC
-- MAGIC Lo que se evalúa:
-- MAGIC - Tipos correctos (fechas como fecha, montos como número).
-- MAGIC - Nulos tratados con una regla que puedas explicar.
-- MAGIC - Deduplicación por la llave del negocio.
-- MAGIC - Al menos un join que enriquezca la tabla.
-- MAGIC - Una celda de métricas antes y después.
-- MAGIC
-- MAGIC Silver queda en tres tablas:
-- MAGIC
-- MAGIC | Tabla | Qué guarda |
-- MAGIC |---|---|
-- MAGIC | `silver.mediciones` | Todas las mediciones de la NASA con tipos correctos y sin copias exactas. Un planeta aparece una vez por cada artículo que lo midió |
-- MAGIC | `silver.habitabilidad_expertos` | El catálogo de la UPR limpio, un registro por planeta |
-- MAGIC | `silver.planetas` | **Un registro por planeta**: la medición oficial más reciente, con los nulos tratados y unida a la evaluación de los expertos |

-- COMMAND ----------

CREATE WIDGET TEXT catalogo DEFAULT 'pf_ledezma';

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalogo);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 1. Mediciones: tipos correctos y sin copias exactas
-- MAGIC - `pl_pubdate` llega como texto en tres formatos (`2018-10`, `2015-09-24`, `2017-08-31 00:00`) y lo convierto a fecha.
-- MAGIC - Las marcas 0/1 pasan a verdadero/falso.
-- MAGIC - La referencia llega como HTML (`<a href=...>Jenkins et al. 2015</a>`); separo el autor y el link del artículo.
-- MAGIC - El lugar de descubrimiento viene como `Ground` y `ground`; lo dejo con una sola forma.
-- MAGIC - Las filas idénticas en todas sus columnas se quedan una sola vez.

-- COMMAND ----------

CREATE OR REPLACE TABLE silver.mediciones
CLUSTER BY (planeta)
COMMENT 'Todas las mediciones de la NASA con tipos correctos y sin copias exactas. Una fila por cada artículo que midió un planeta.'
AS
SELECT DISTINCT
  trim(pl_name)                                    AS planeta,
  trim(hostname)                                   AS estrella,
  default_flag = 1                                 AS es_oficial,
  coalesce(pl_controv_flag = 1, false)             AS en_disputa,
  discoverymethod                                  AS metodo_descubrimiento,
  disc_year                                        AS anio_descubrimiento,
  disc_facility                                    AS instalacion,
  initcap(disc_locale)                             AS lugar_descubrimiento,
  disc_telescope                                   AS telescopio,
  soltype                                          AS tipo_solucion,
  regexp_extract(pl_refname, '>([^<]+)</a>', 1)    AS referencia,
  regexp_extract(pl_refname, 'href=([^ >]+)', 1)   AS link_referencia,
  to_date(coalesce(
    try_to_timestamp(pl_pubdate, 'yyyy-MM-dd HH:mm'),
    try_to_timestamp(pl_pubdate, 'yyyy-MM-dd'),
    try_to_timestamp(pl_pubdate, 'yyyy-MM')))      AS fecha_publicacion,
  to_date(releasedate)                             AS fecha_liberacion,
  pl_orbper                                        AS periodo_dias,
  pl_orbsmax                                       AS distancia_orbital_ua,
  pl_rade                                          AS radio_tierras,
  pl_bmasse                                        AS masa_tierras,
  pl_orbeccen                                      AS excentricidad,
  pl_insol                                         AS insolacion_tierras,
  pl_eqt                                           AS temp_equilibrio_k,
  st_spectype                                      AS tipo_espectral,
  st_teff                                          AS temp_estrella_k,
  st_rad                                           AS radio_estrella_soles,
  st_mass                                          AS masa_estrella_soles,
  st_lum                                           AS luminosidad_log10,
  ra,
  dec,
  sy_dist                                          AS distancia_pc,
  sy_snum                                          AS estrellas_en_sistema,
  sy_pnum                                          AS planetas_en_sistema,
  archivo_origen,
  fecha_ingesta
FROM bronze.mediciones_raw;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 2. Catálogo de expertos limpio

-- COMMAND ----------

CREATE OR REPLACE TABLE silver.habitabilidad_expertos
COMMENT 'Habitable Worlds Catalog (PHL @ UPR Arecibo) limpio: un registro por planeta con la evaluación de los expertos'
AS
SELECT
  trim(P_NAME)                                                AS planeta,
  P_ESI                                                       AS esi_expertos,
  CASE P_HABITABLE WHEN 1 THEN 'conservador'
                   WHEN 2 THEN 'optimista'
                   ELSE 'no' END                              AS habitable_expertos,
  nullif(trim(P_TYPE), '')                                    AS tipo_expertos,
  S_DISTANCE                                                  AS distancia_pc_expertos,
  to_date(P_UPDATE)                                           AS actualizado_expertos
FROM bronze.habitabilidad_raw
QUALIFY row_number() OVER (PARTITION BY trim(P_NAME) ORDER BY P_UPDATE DESC) = 1;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### 3. Un registro por planeta
-- MAGIC
-- MAGIC **Llave del negocio:** el nombre del planeta (`planeta`).
-- MAGIC
-- MAGIC **Deduplicación:** me quedo con la medición **oficial** (la que la NASA marca con `default_flag`) **más reciente**. Si el planeta todavía no tiene medición oficial en lo que llevo cargado, me quedo con la más reciente.
-- MAGIC
-- MAGIC **Nulos**, en este orden:
-- MAGIC 1. Si la medición oficial no trae el dato, lo tomo de la publicación más reciente del mismo planeta que sí lo tenga.
-- MAGIC 2. Si ninguna publicación trae la insolación, la calculo con la luminosidad de la estrella y la distancia orbital: `S = 10^luminosidad / distancia²`.
-- MAGIC 3. Si ninguna trae el radio pero sí la masa, lo estimo con la relación masa-radio de Chen y Kipping (2017).
-- MAGIC 4. Si la NASA no trae la distancia (pasa con todo el sistema TRAPPIST-1), uso la del catálogo de la UPR.
-- MAGIC 5. Lo que siga faltando se queda nulo. No lo relleno con promedios.
-- MAGIC
-- MAGIC Las columnas `fuente_radio`, `fuente_insolacion` y `fuente_distancia` dicen de dónde salió cada valor.
-- MAGIC
-- MAGIC **Join:** con el catálogo de expertos por nombre del planeta. Trae la evaluación de los expertos y la distancia que le falta a la NASA.

-- COMMAND ----------

CREATE OR REPLACE TABLE silver.planetas
COMMENT 'Un registro por planeta: la medición oficial más reciente, con los nulos tratados y unida a la evaluación de los expertos de la UPR'
AS
WITH base AS (
  SELECT *
  FROM silver.mediciones
  QUALIFY row_number() OVER (
    PARTITION BY planeta
    ORDER BY es_oficial DESC, fecha_liberacion DESC, fecha_publicacion DESC) = 1
),
respaldo AS (
  -- Para cada dato, el valor de la publicación más reciente que sí lo trae
  SELECT
    planeta,
    max_by(radio_tierras, fecha_publicacion)        FILTER (WHERE radio_tierras IS NOT NULL)        AS radio,
    max_by(masa_tierras, fecha_publicacion)         FILTER (WHERE masa_tierras IS NOT NULL)         AS masa,
    max_by(insolacion_tierras, fecha_publicacion)   FILTER (WHERE insolacion_tierras IS NOT NULL)   AS insolacion,
    max_by(temp_equilibrio_k, fecha_publicacion)    FILTER (WHERE temp_equilibrio_k IS NOT NULL)    AS temp_equilibrio,
    max_by(distancia_orbital_ua, fecha_publicacion) FILTER (WHERE distancia_orbital_ua IS NOT NULL) AS distancia_orbital,
    max_by(luminosidad_log10, fecha_publicacion)    FILTER (WHERE luminosidad_log10 IS NOT NULL)    AS luminosidad,
    max_by(temp_estrella_k, fecha_publicacion)      FILTER (WHERE temp_estrella_k IS NOT NULL)      AS temp_estrella,
    max_by(distancia_pc, fecha_publicacion)         FILTER (WHERE distancia_pc IS NOT NULL)         AS distancia_pc,
    count(*)                                                                                        AS mediciones
  FROM silver.mediciones
  GROUP BY planeta
),
completos AS (
  SELECT
    b.planeta, b.estrella, b.en_disputa, b.metodo_descubrimiento, b.anio_descubrimiento, b.instalacion,
    b.lugar_descubrimiento, b.telescopio, b.referencia, b.link_referencia, b.fecha_publicacion,
    b.tipo_espectral, b.ra, b.dec, b.estrellas_en_sistema, b.planetas_en_sistema,
    b.periodo_dias, b.excentricidad, r.mediciones,
    coalesce(b.temp_estrella_k, r.temp_estrella)          AS temp_estrella_k,
    coalesce(b.distancia_pc, r.distancia_pc)               AS distancia_pc,
    coalesce(b.masa_tierras, r.masa)                       AS masa_tierras,
    coalesce(b.temp_equilibrio_k, r.temp_equilibrio)       AS temp_equilibrio_k,
    coalesce(b.distancia_orbital_ua, r.distancia_orbital)  AS distancia_orbital_ua,
    coalesce(b.luminosidad_log10, r.luminosidad)           AS luminosidad_log10,
    b.radio_tierras                                        AS radio_oficial,
    r.radio                                                AS radio_otra_publicacion,
    b.insolacion_tierras                                   AS insolacion_oficial,
    r.insolacion                                           AS insolacion_otra_publicacion
  FROM base b
  JOIN respaldo r USING (planeta)
),
tratados AS (
  SELECT
    *,
    coalesce(
      radio_oficial,
      radio_otra_publicacion,
      CASE WHEN masa_tierras < 2.04 THEN power(masa_tierras, 0.279)
           WHEN masa_tierras < 132  THEN 0.80811 * power(masa_tierras, 0.589)
           ELSE 17.739 * power(masa_tierras, -0.044) END)                         AS radio_tierras,
    CASE WHEN radio_oficial IS NOT NULL THEN 'medición oficial'
         WHEN radio_otra_publicacion IS NOT NULL THEN 'otra publicación'
         WHEN masa_tierras IS NOT NULL THEN 'estimado con la masa' END             AS fuente_radio,
    coalesce(
      insolacion_oficial,
      insolacion_otra_publicacion,
      try_divide(power(10, luminosidad_log10), power(distancia_orbital_ua, 2)))   AS insolacion_tierras,
    CASE WHEN insolacion_oficial IS NOT NULL THEN 'medición oficial'
         WHEN insolacion_otra_publicacion IS NOT NULL THEN 'otra publicación'
         WHEN luminosidad_log10 IS NOT NULL AND distancia_orbital_ua > 0
           THEN 'calculada con la luminosidad' END                                  AS fuente_insolacion
  FROM completos
)
SELECT
  t.* EXCEPT (radio_oficial, radio_otra_publicacion, insolacion_oficial, insolacion_otra_publicacion, distancia_pc),
  coalesce(t.distancia_pc, e.distancia_pc_expertos)                  AS distancia_pc,
  CASE WHEN t.distancia_pc IS NOT NULL THEN 'NASA'
       WHEN e.distancia_pc_expertos IS NOT NULL THEN 'catálogo UPR' END AS fuente_distancia,
  round(coalesce(t.distancia_pc, e.distancia_pc_expertos) * 3.26156, 2) AS distancia_anios_luz,
  t.radio_tierras IS NOT NULL AND t.insolacion_tierras IS NOT NULL   AS datos_suficientes,
  e.esi_expertos,
  e.habitable_expertos,
  e.tipo_expertos,
  e.planeta IS NOT NULL                                              AS evaluado_por_expertos
FROM tratados t
LEFT JOIN silver.habitabilidad_expertos e ON t.planeta = e.planeta;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Métricas antes y después

-- COMMAND ----------

WITH bronze_oficial AS (
  SELECT * FROM bronze.mediciones_raw WHERE default_flag = 1
),
metricas AS (
  SELECT 1 AS orden, 'Filas' AS metrica,
         format_number((SELECT count(*) FROM bronze.mediciones_raw), 0) AS bronze,
         format_number((SELECT count(*) FROM silver.mediciones), 0) || ' mediciones · '
           || format_number((SELECT count(*) FROM silver.planetas), 0) || ' planetas' AS silver
  UNION ALL
  SELECT 2, 'Copias exactas de una fila',
         format_number((SELECT count(*) FROM bronze.mediciones_raw)
                       - (SELECT count(*) FROM (SELECT DISTINCT * EXCEPT (archivo_origen, fecha_ingesta, _rescued_data)
                                                FROM bronze.mediciones_raw)), 0),
         format_number((SELECT count(*) FROM silver.mediciones)
                       - (SELECT count(*) FROM (SELECT DISTINCT * EXCEPT (archivo_origen, fecha_ingesta)
                                                FROM silver.mediciones)), 0)
  UNION ALL
  SELECT 3, 'Máximo de filas por planeta',
         (SELECT string(max(n)) FROM (SELECT count(*) AS n FROM bronze.mediciones_raw GROUP BY pl_name)),
         (SELECT string(max(n)) FROM (SELECT count(*) AS n FROM silver.planetas GROUP BY planeta))
  UNION ALL
  SELECT 4, 'Planetas sin insolación (fila oficial)',
         (SELECT format_number(100 * avg(CASE WHEN pl_insol IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM bronze_oficial),
         (SELECT format_number(100 * avg(CASE WHEN insolacion_tierras IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM silver.planetas)
  UNION ALL
  SELECT 5, 'Planetas sin radio (fila oficial)',
         (SELECT format_number(100 * avg(CASE WHEN pl_rade IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM bronze_oficial),
         (SELECT format_number(100 * avg(CASE WHEN radio_tierras IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM silver.planetas)
  UNION ALL
  SELECT 6, 'Planetas sin distancia (fila oficial)',
         (SELECT format_number(100 * avg(CASE WHEN sy_dist IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM bronze_oficial),
         (SELECT format_number(100 * avg(CASE WHEN distancia_pc IS NULL THEN 1 ELSE 0 END), 1) || '%' FROM silver.planetas)
  UNION ALL
  SELECT 7, 'Formatos de fecha de publicación',
         (SELECT string(count(DISTINCT length(pl_pubdate))) || ' (texto)' FROM bronze.mediciones_raw),
         '1 (fecha)'
  UNION ALL
  SELECT 8, 'Formas de escribir el lugar de descubrimiento',
         (SELECT string(count(DISTINCT disc_locale)) FROM bronze.mediciones_raw),
         (SELECT string(count(DISTINCT lugar_descubrimiento)) FROM silver.mediciones)
  UNION ALL
  SELECT 9, 'Planetas con evaluación de expertos (join)',
         '—',
         (SELECT format_number(count_if(evaluado_por_expertos), 0) || ' de ' || format_number(count(*), 0) FROM silver.planetas)
  UNION ALL
  SELECT 10, 'Planetas con datos suficientes para el ranking',
         (SELECT format_number(count_if(pl_rade IS NOT NULL AND pl_insol IS NOT NULL), 0) FROM bronze_oficial),
         (SELECT format_number(count_if(datos_suficientes), 0) FROM silver.planetas)
)
SELECT metrica, bronze AS antes_bronze, silver AS despues_silver
FROM metricas
ORDER BY orden;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### De dónde salió cada radio y cada insolación

-- COMMAND ----------

SELECT 'radio' AS dato, coalesce(fuente_radio, 'sin dato') AS fuente, count(*) AS planetas
FROM silver.planetas GROUP BY ALL
UNION ALL
SELECT 'insolación', coalesce(fuente_insolacion, 'sin dato'), count(*)
FROM silver.planetas GROUP BY ALL
ORDER BY dato, planetas DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### TU RESPUESTA
-- MAGIC ¿Qué regla usaste para los nulos y los duplicados, y por qué esa y no otra?
-- MAGIC
-- MAGIC Con los duplicados tuve dos casos. El primero son copias exactas: 59 filas que venían repetidas tal cual y que simplemente quito (en las métricas pasan de 59 a 0). El segundo es el importante: un mismo planeta aparece una vez por cada artículo que lo midió, hasta 34 veces. La llave del negocio es el nombre del planeta y me quedo con la medición que la NASA marca como oficial, la más reciente. Si todavía no ha llegado la oficial (me pasó con el lote 1, donde a varios planetas les faltaba) uso la más reciente. Así quedan 6,437 planetas, uno por fila.
-- MAGIC
-- MAGIC Para los nulos no quise rellenar con promedios, porque cada planeta es distinto y un promedio sería inventar el dato. Primero busco el valor en otra publicación del mismo planeta, que es una medición real. Si nadie lo midió, lo calculo: la insolación con la luminosidad de la estrella y la distancia, y el radio con la masa (relación de Chen y Kipping). La distancia que no trae la NASA, como la de TRAPPIST-1, la saco del catálogo de la UPR con el join. Lo que sigue faltando se queda nulo y ese planeta no entra al ranking. Con eso la insolación pasó de faltar en el 85.3% de los planetas a 17.8%, y los planetas con datos suficientes para el ranking pasaron de 826 a 5,290.
